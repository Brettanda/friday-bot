from __future__ import annotations

import asyncio
import datetime
import io
import logging
import os
import sys
import traceback
import typing
from collections import Counter
from typing import TYPE_CHECKING, List, Optional, Set

import asyncpg
import discord
from discord.ext import commands  # , tasks
from wavelink import errors as wavelink_errors

# from discord_slash.http import SlashCommandRequest
from functions import (MessageColors, MyContext,  # , FakeInteractionMessage
                       cache, embed, exceptions, relay_info, time, views)

# import mysql.connector


if TYPE_CHECKING:
  from index import Friday

  class CommandError(commands.CommandError):
    log: Optional[bool]

# import discord_slash

log = logging.getLogger(__name__)

# with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.json')) as f:
#   config = json.load(f)

# def is_enabled(ctx):
#   if not ctx.enabled:
#     raise commands.CheckFailure("Currently I am disabled, my boss has been notified, please try again later :)")
#   return True


class Config:
  __slots__ = ("bot", "id", "chat_channel", "disabled_commands", "restricted_commands", "bot_channel", "tier", "lang",)

  def __init__(self, *, record: asyncpg.Record, bot: Friday):
    self.bot: Friday = bot
    self.id: int = int(record["id"], base=10)
    self.chat_channel: discord.TextChannel = record["chatchannel"]
    self.disabled_commands: Set[str] = set(record["disabled_commands"] or [])
    self.restricted_commands: Set[str] = set(record["restricted_commands"] or [])
    self.bot_channel: Optional[int] = int(record["botchannel"], base=10) if record["botchannel"] else None
    self.tier: str = record["tier"]
    self.lang: str = record["lang"]


class CustomWebhook(discord.Webhook):
  async def safe_send(self, content: str, *, escape_mentions=True, **kwargs) -> typing.Optional[discord.WebhookMessage]:
    """something"""

    if escape_mentions:
      content = discord.utils.escape_mentions(content)

    if len(content) > 2000:
      fp = io.BytesIO(content.encode())
      kwargs.pop("file", None)
      return await self.send(file=discord.File(fp, filename="message_too_long.txt"), **kwargs)
    else:
      return await self.send(content, **kwargs)


class Log(commands.Cog):
  """Everything that is required for the bot to run but can also be reloaded without restarting the bot"""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot

    self.spam_control = commands.CooldownMapping.from_cooldown(5, 15.0, commands.BucketType.user)
    self.super_spam_control = commands.CooldownMapping.from_cooldown(5, 60, commands.BucketType.user)

    self.super_spam_counter = None

    self._auto_spam_count = Counter()

    self.bot.process_commands = self.process_commands
    # self.bot.on_error = self.on_error

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def bot_check(self, ctx: MyContext) -> bool:
    if hasattr(ctx.channel, "type") and ctx.channel.type == discord.ChannelType.private:
      return True

    return await commands.bot_has_permissions(
        send_messages=True,
        read_messages=True,
        embed_links=True,
        add_reactions=True,
    ).predicate(ctx)

  async def cog_load(self) -> None:
    query = "SELECT id,lang FROM servers WHERE lang IS NOT NULL;"
    records = await self.bot.pool.fetch(query)
    new_query = ""
    total = len(records)
    completed = 0
    for r in records:
      await self.bot.languages.put(r["id"], r["lang"])
      new_query += f"UPDATE servers SET lang = NULL WHERE id = {r['id']}::text;"
      completed += 1
    if new_query:
      await self.bot.pool.execute(new_query)
    log.info(f"Moved {completed}/{total} languages to new system")

  @commands.Cog.listener()
  async def on_shard_connect(self, shard_id):
    await relay_info(f"Shard #{shard_id} has connected", self.bot, logger=log)

  @commands.Cog.listener()
  async def on_connect(self):
    log.debug("Connected")

  @commands.Cog.listener()
  async def on_ready(self):
    if not self.bot.views_loaded:
      self.bot.add_view(views.Links())
      self.bot.add_view(views.StopButton())
    if not hasattr(self.bot, "uptime"):
      self.bot.uptime = discord.utils.utcnow()

    await relay_info(f"Apart of {len(self.bot.guilds)} guilds", self.bot, logger=log)
    self.bot.ready = True

  @commands.Cog.listener()
  async def on_shard_ready(self, shard_id):
    shard = self.bot.get_shard(shard_id)
    await relay_info(f"Logged on as #{shard_id} {self.bot.user}! - {shard and shard.latency*1000:,.0f} ms", self.bot, logger=log)

  @commands.Cog.listener()
  async def on_disconnect(self):
    log.debug("Disconnected")

  @commands.Cog.listener()
  async def on_shard_disconnect(self, shard_id):
    log.info(f"Shard #{shard_id} has disconnected")

  @commands.Cog.listener()
  async def on_shard_reconnect(self, shard_id):
    log.info(f"Shard #{shard_id} has reconnected")

  @commands.Cog.listener()
  async def on_resumed(self):
    log.debug("Resumed")

  @commands.Cog.listener()
  async def on_shard_resumed(self, shard_id):
    log.info(f"Shard #{shard_id} has resumed")
    self.bot.resumes[shard_id].append(discord.utils.utcnow())

  @commands.Cog.listener()
  async def on_guild_join(self, guild: discord.Guild):
    await self.bot.wait_until_ready()
    await self.bot.pool.execute(f"INSERT INTO servers (id,lang) VALUES ({str(guild.id)},'{guild.preferred_locale.value.split('-')[0]}') ON CONFLICT DO NOTHING")
    await relay_info(f"I have joined a new guild, making the total **{len(self.bot.guilds)}**", self.bot, short=f"I have joined ({guild} [{guild.id}]), making the total {len(self.bot.guilds)}", webhook=self.log_join, logger=log)

  @commands.Cog.listener()
  async def on_guild_remove(self, guild):
    await self.bot.wait_until_ready()
    await relay_info(f"I have been removed from a guild, making the total **{len(self.bot.guilds)}**", self.bot, short=f"I have been removed from ({guild} [{guild.id}]), making the total {len(self.bot.guilds)}", webhook=self.log_join, logger=log)

  @commands.Cog.listener()
  async def on_message_edit(self, before, after):
    if after.author.bot or before.content == after.content:
      return
    await self.bot.process_commands(after)

  @commands.Cog.listener()
  async def on_command_completion(self, ctx: "MyContext"):
    log.debug(f"Finished Command: {ctx.message.clean_content.encode('unicode_escape')}")

  @commands.Cog.listener()
  async def on_slash_command(self, ctx):
    log.info(f"Slash Command: {ctx.command} {ctx.kwargs}")

  # @commands.Cog.listener()
  # async def on_slash_command_error(self, ctx: SlashContext, ex):
  #   print(ex)
  #   if not ctx.responded:
  #     if ctx._deffered_hidden or not ctx.deferred:
  #       await ctx.send(hidden=True, content=str(ex) or "An error has occured, try again later.")
  #     else:
  #       await ctx.send(embed=embed(title=str(ex) or "An error has occured, try again later.", color=MessageColors.error()))
  #   if not isinstance(ex, (
  #           discord.NotFound,
  #           commands.CheckFailure,
  #           commands.MissingPermissions,
  #           commands.BotMissingPermissions,
  #           commands.NoPrivateMessage,
  #           commands.MaxConcurrencyReached)) and (not hasattr(ex, "log") or (hasattr(ex, "log") and ex.log is True)):
  #     raise ex

  # async def convert_param(self, ctx: SlashContext, option, param):
  #   value = option["value"]
  #   if param.annotation != inspect.Parameter.empty:
  #     value = await commands.run_converters(ctx, param.annotation, value, 0)
  #   return value

  @commands.Cog.listener()
  async def on_interaction(self, interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.application_command:
      log.info(f"Interaction: {interaction.data and interaction.data.get('custom_id','No ID')} {interaction.type}")

    # if interaction.type == discord.InteractionType.application_command:
    #   command = self.bot.get_command(interaction.data["name"])

    #   if command is None:
    #     return await relay_info(f"Missing slash command: {interaction.data['name']}", self.bot, webhook=self.log_errors)

    #   ctx = MyContext(prefix="/", view=StringView(interaction.data["name"]), bot=self.bot, message=FakeInteractionMessage(self.bot, interaction))
    #   options = {option["name"]: option for option in interaction.data.get("options", {})}
    #   params, kwargs = [], {}
    #   for name, param in command.clean_params.items():
    #     option = options.get(name)
    #     if not option:
    #       option = param.default
    #     else:
    #       option = await self.convert_param(ctx, option, param)
    #     if param.kind == inspect.Parameter.KEYWORD_ONLY:
    #       kwargs[name] = option
    #     else:
    #       params.append(option)

    #   async def fallback():
    #     await asyncio.sleep(2)
    #     if interaction.response.is_done():
    #       return
    #     try:
    #       await interaction.response.defer()
    #     except Exception:
    #       pass
    #   self.bot.loop.create_task(fallback())
    #   try:
    #     self.bot.dispatch("command", ctx)
    #     if await command.can_run(ctx):
    #       await command(ctx, *params, **kwargs)
    #   except Exception as e:
    #     self.bot.dispatch("command_error", ctx, e)

  # @commands.Cog.listener()
  # async def on_component_callback_error(self, ctx: ComponentContext, ex: Exception):
  #   if not ctx.responded:
  #     if ctx._deferred_hidden or not ctx.deferred:
  #       await ctx.send(hidden=True, content=str(ex) or "An error has occured, try again later.")
  #     else:
  #       await ctx.send(embed=embed(title=str(ex) or "An error has occured, try again later.", color=MessageColors.error()))
  #   if not isinstance(ex, (
  #           discord.NotFound,
  #           commands.CheckFailure,
  #           commands.MissingPermissions,
  #           commands.BotMissingPermissions,
  #           commands.NoPrivateMessage,
  #           commands.MaxConcurrencyReached)) and (not hasattr(ex, "log") or (hasattr(ex, "log") and ex.log is True)):
  #     raise ex

  async def bot_check_once(self, ctx: MyContext):
    if ctx.command.cog_name not in ("Dev", "Config"):
      if ctx.author.id in self.bot.blacklist:
        return False

      if ctx.guild is not None and ctx.guild.id in self.bot.blacklist:
        return False

      if ctx.guild:
        config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
        if not config:
          await ctx.db.execute(f"INSERT INTO servers (id,lang) VALUES ({str(ctx.guild.id)},'{ctx.guild.preferred_locale.value.split('-')[0]}') ON CONFLICT DO NOTHING")
          self.get_guild_config.invalidate(self, ctx.guild.id)
          config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
        if config is not None:
          if ctx.command.name in config.disabled_commands:
            return False

          if config.bot_channel is not None and ctx.channel.id != config.bot_channel:
            if ctx.command.name in config.restricted_commands and not ctx.author.guild_permissions.manage_guild:  # type: ignore
              await ctx.send(f"<#{config.bot_channel}>", embed=embed(title="This command is restricted to the bot channel.", color=MessageColors.error()), delete_after=30, ephemeral=True)
              return False
    return True

  async def process_commands(self, message):
    ctx = await self.bot.get_context(message, cls=MyContext)

    if ctx.command is None:
      return

    current = message.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()
    bucket = self.spam_control.get_bucket(message, current)
    retry_after = bucket and bucket.update_rate_limit(current)
    author_id = message.author.id

    super_bucket = self.super_spam_control.get_bucket(message, current)
    super_retry_after = super_bucket and super_bucket.get_retry_after(current)

    if retry_after and author_id != self.bot.owner_id and author_id != 892865928520413245:
      self._auto_spam_count[author_id] += 1
      super_retry_after = super_bucket and super_bucket.update_rate_limit(current)
      if super_retry_after and self._auto_spam_count[author_id] == 5:
        await self.log_spammer(ctx, message, retry_after, notify=True)
      elif self._auto_spam_count[author_id] > 5:
        del self._auto_spam_count[author_id]
      else:
        await self.log_spammer(ctx, message, retry_after)
      return
    else:
      self._auto_spam_count.pop(author_id, None)

    if super_retry_after:
      return

    try:
      await self.bot.invoke(ctx)
    finally:
      # Just in case
      await ctx.release()

  def get_prefixes(self) -> List[str]:
    return ["/", "!", "f!", "!f", "%", ">", "?", "-", "(", ")"]

  @cache.cache(ignore_kwargs=True)
  async def get_guild_config(self, guild_id: int, *, connection: Optional[asyncpg.Pool | asyncpg.Connection] = None) -> Config:
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1;"
    conn = connection or self.bot.pool
    record = await conn.fetchrow(query, str(guild_id))
    log.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
    if not record:
      raise ValueError("Server not found.")
    return Config(record=record, bot=self.bot)

  @discord.utils.cached_property
  def log_chat(self) -> CustomWebhook:
    return CustomWebhook.partial(os.environ.get("WEBHOOKCHATID"), os.environ.get("WEBHOOKCHATTOKEN"), session=self.bot.session)  # type: ignore

  @discord.utils.cached_property
  def log_info(self) -> CustomWebhook:
    return CustomWebhook.partial(os.environ.get("WEBHOOKINFOID"), os.environ.get("WEBHOOKINFOTOKEN"), session=self.bot.session)  # type: ignore

  @discord.utils.cached_property
  def log_errors(self) -> CustomWebhook:
    return CustomWebhook.partial(os.environ.get("WEBHOOKERRORSID"), os.environ.get("WEBHOOKERRORSTOKEN"), session=self.bot.session)  # type: ignore

  @discord.utils.cached_property
  def log_join(self) -> CustomWebhook:
    return CustomWebhook.partial(os.environ.get("WEBHOOKJOINID"), os.environ.get("WEBHOOKJOINTOKEN"), session=self.bot.session)  # type: ignore

  async def log_spammer(self, ctx, message, retry_after, *, notify=False):
    guild_id = getattr(ctx.guild, "id", None)
    log.warning(f"Spamming: {{User: {message.author.id}, Guild: {guild_id}, Retry: {retry_after}}}")

  # @commands.Cog.listener()
  # async def on_application_command_error(self, ctx: discord.ApplicationContext, error: Exception):
  #   just_send = (commands.DisabledCommand, commands.BotMissingPermissions, commands.MissingPermissions, commands.RoleNotFound,)
  #   error = getattr(error, 'original', error)
  #   # if hasattr(error, "log") and error.log is False:
  #   #   return

  #   # if isinstance(error, just_send):
  #   log.error(f"{error}")
  #   await ctx.respond(embed=embed(title=str(error) or "An error has occured, try again later.", color=MessageColors.error()), ephemeral=True)

  @commands.Cog.listener()
  async def on_command_error(self, ctx: MyContext, error: CommandError):
    if hasattr(ctx.command, 'on_error'):
      return

    # if ctx.cog:
    #   if ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
    #     return

    ignored = (commands.CommandNotFound, commands.NotOwner, )
    wave_errors = (wavelink_errors.LoadTrackError, wavelink_errors.WavelinkError,)
    just_send = (commands.DisabledCommand, commands.MissingPermissions, commands.RoleNotFound, commands.MaxConcurrencyReached, asyncio.TimeoutError, commands.BadArgument, exceptions.RequiredTier)
    error = getattr(error, 'original', error)

    if isinstance(error, (*ignored, *wave_errors)) or (hasattr(error, "log") and error and error.log is False):
      log.warning("Ignored error called: {}".format(error))
      return

    if isinstance(error, just_send):
      await ctx.send(embed=embed(title=str(error), color=MessageColors.error()), ephemeral=True)
    elif isinstance(error, commands.BotMissingPermissions):
      if "embed_links" in error.missing_permissions:
        await ctx.send(str(error), ephemeral=True)
      else:
        await ctx.send(embed=embed(title=str(error), color=MessageColors.error()), ephemeral=True)
    elif isinstance(error, commands.BadUnionArgument) and "into Member or User." in str(error):
      await ctx.send(embed=embed(title="Invalid user. Please mention a user or provide a user ID.", color=MessageColors.error()))
    elif isinstance(error, (commands.MissingRequiredArgument, commands.TooManyArguments)):
      await ctx.send_help(ctx.command)
    elif isinstance(error, commands.CommandOnCooldown):
      retry_after = discord.utils.utcnow() + datetime.timedelta(seconds=error.retry_after)
      await ctx.send(embed=embed(title=f"This command is on a cooldown, and will be available in `{time.human_timedelta(retry_after)}` or <t:{int(retry_after.timestamp())}:R>", color=MessageColors.error()), ephemeral=True)
    elif isinstance(error, (exceptions.RequiredTier, exceptions.NotInSupportServer)):
      await ctx.send(embed=embed(title=str(error), color=MessageColors.error()), ephemeral=True)
    elif isinstance(error, commands.CheckFailure):
      log.warn(f"{ctx.guild and ctx.guild.id or 'Private Message'} {ctx.channel} {ctx.author} {error}")
    elif isinstance(error, commands.NoPrivateMessage):
      await ctx.send(embed=embed(title="This command does not work in non-server text channels", color=MessageColors.error()), ephemeral=True)
    elif isinstance(error, OverflowError):
      await ctx.send(embed=embed(title="An arguments number is too large.", color=MessageColors.error()), ephemeral=True)
    elif isinstance(error, commands.CommandInvokeError):
      original = error.original
      if not isinstance(original, discord.HTTPException):
        print(f"In {ctx.command.qualified_name}:", file=sys.stderr)
        traceback.print_tb(original.__traceback__)
        log.error(f"{original.__class__.__name__}: {original}", sys.stderr.readline)
    else:
      if error:
        log.error('Ignoring exception in command {}:'.format(ctx.command), exc_info=(type(error), error, error.__traceback__))
      if not self.bot.prod and not self.bot.canary:
        return
      try:
        await self.log_errors.safe_send(username=self.bot.user.name, avatar_url=self.bot.user.display_avatar.url, content=f"Ignoring exception in command {ctx.command}:\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}")
      except Exception as e:
        log.error(f"ERROR while ignoring exception in command {ctx.command}: {e}")
      else:
        log.info("ERROR sent")

  async def on_error(self, event: str, *args, **kwargs):
    trace = traceback.format_exc()
    log.error(f"ERROR in {event}: ", exc_info=trace)  # type: ignore
    if not self.bot.prod and not self.bot.canary:
      return
    try:
      await self.log_errors.safe_send(username=self.bot.user.name, avatar_url=self.bot.user.display_avatar.url, content=f"```\nERROR in {event}: \n{trace}\n```")
    except Exception as e:
      log.error(f"ERROR while logging {event}: {e}")
    else:
      log.info("ERROR sent")


async def setup(bot):
  await bot.add_cog(Log(bot))
