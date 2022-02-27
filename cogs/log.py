import sys
import datetime
import discord
import asyncio
import io
# import mysql.connector

import typing
from typing import TYPE_CHECKING
from pycord.wavelink import errors as wavelink_errors
from discord.ext import commands  # , tasks
# from discord_slash.http import SlashCommandRequest
from functions import MessageColors, embed, relay_info, exceptions, config, views, MyContext, cache  # , FakeInteractionMessage
import traceback

from collections import Counter

import os

if TYPE_CHECKING:
  from index import Friday as Bot

# import discord_slash


# with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.json')) as f:
#   config = json.load(f)

# def is_enabled(ctx):
#   if not ctx.enabled:
#     raise commands.CheckFailure("Currently I am disabled, my boss has been notified, please try again later :)")
#   return True

class Config:
  __slots__ = ("bot", "id", "chat_channel", "disabled_commands", "restricted_commands", "bot_channel", "tier", "lang",)

  @classmethod
  async def from_record(cls, record, bot):
    self = cls()

    self.bot: "Bot" = bot
    self.id: int = int(record["id"], base=10)
    self.chat_channel = record["chatchannel"]
    self.disabled_commands = set(record["disabled_commands"] or [])
    self.restricted_commands = set(record["restricted_commands"] or [])
    self.bot_channel = int(record["botchannel"], base=10) if record["botchannel"] else None
    self.tier = record["tier"]
    self.lang = record["lang"]
    return self


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

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.loop = bot.loop
    self.loop.create_task(self.setup())

    self.spam_control = commands.CooldownMapping.from_cooldown(5, 15.0, commands.BucketType.user)
    self.super_spam_control = commands.CooldownMapping.from_cooldown(5, 60, commands.BucketType.user)

    self.super_spam_counter = None

    self._auto_spam_count = Counter()

    self.logger = self.bot.logger

    # if not hasattr(self.bot, "slash"):
    #   self.bot.slash = SlashCommand(self.bot, sync_commands=True, sync_on_cog_reload=True)  # , debug_guild=243159711237537802)

    self.bot.process_commands = self.process_commands
    # self.bot.on_error = self.on_error

    # self.check_for_mydb.start()

    self.bot.add_check(self.check_perms)

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def setup(self) -> None:
    if not hasattr(self, "bot_managers"):
      self.bot_managers = {}
      for guild_id, role_id in await self.bot.db.query("SELECT id,bot_manager FROM servers"):
        if role_id is not None:
          self.bot_managers.update({str(guild_id): str(role_id)})

  def check_perms(self, ctx):
    if hasattr(ctx.channel, "type") and ctx.channel.type == discord.ChannelType.private:
      return True

    required_perms = [("send_messages", True), ("read_messages", True), ("embed_links", True), ("add_reactions", True)]
    guild = ctx.guild
    me = guild.me if guild is not None else ctx.bot.user
    permissions = ctx.channel.permissions_for(me)
    missing = [perm for perm, value in required_perms if getattr(permissions, perm) != value]

    if not missing:
      return True

    raise commands.BotMissingPermissions(missing)

  # @tasks.loop(seconds=10.0)
  # async def check_for_mydb(self):
  #   try:
  #     self.mydb.ping(reconnect=True, attempts=10, delay=0.1)
  #   except mysql.connector.InterfaceError as e:
  #     await relay_info("Disconnected from MYDB", self.bot, logger=self.logger)
  #     raise e

  # @check_for_mydb.before_loop
  # async def before_check_for_mydb(self):
  #   await self.bot.wait_until_ready()
  #   while self.bot.is_closed():
  #     await asyncio.sleep(0.1)

  # def cog_unload(self):
    # self.check_for_mydb.stop()

  @commands.Cog.listener()
  async def on_shard_connect(self, shard_id):
    await relay_info(f"Shard #{shard_id} has connected", self.bot, logger=self.logger)

  @commands.Cog.listener()
  async def on_connect(self):
    self.logger.debug("Connected")

  @commands.Cog.listener()
  async def on_ready(self):
    if not self.bot.views_loaded:
      self.bot.add_view(views.Links())
      self.bot.add_view(views.StopButton())
    if not hasattr(self.bot, "uptime"):
      self.bot.uptime = discord.utils.utcnow()

    await relay_info(f"Apart of {len(self.bot.guilds)} guilds", self.bot, logger=self.logger)
    self.bot.ready = True

  @commands.Cog.listener()
  async def on_shard_ready(self, shard_id):
    await relay_info(f"Logged on as #{shard_id} {self.bot.user}! - {self.bot.get_shard(shard_id).latency*1000:,.0f} ms", self.bot, logger=self.logger)

  @commands.Cog.listener()
  async def on_disconnect(self):
    self.logger.debug("Disconnected")

  @commands.Cog.listener()
  async def on_shard_disconnect(self, shard_id):
    self.logger.info(f"Shard #{shard_id} has disconnected")

  @commands.Cog.listener()
  async def on_shard_reconnect(self, shard_id):
    self.logger.info(f"Shard #{shard_id} has reconnected")

  @commands.Cog.listener()
  async def on_resumed(self):
    self.logger.debug("Resumed")

  @commands.Cog.listener()
  async def on_shard_resumed(self, shard_id):
    self.logger.info(f"Shard #{shard_id} has resumed")
    self.bot.resumes[shard_id].append(discord.utils.utcnow())

  @commands.Cog.listener()
  async def on_guild_join(self, guild: discord.Guild):
    await self.bot.wait_until_ready()
    await self.bot.db.query(f"INSERT INTO servers (id,lang) VALUES ({str(guild.id)},'{guild.preferred_locale.split('-')[0]}') ON CONFLICT DO NOTHING")
    await relay_info(f"I have joined a new guild, making the total **{len(self.bot.guilds)}**", self.bot, short=f"I have joined ({guild} [{guild.id}]), making the total {len(self.bot.guilds)}", webhook=self.log_join, logger=self.logger)

  @commands.Cog.listener()
  async def on_guild_remove(self, guild):
    await self.bot.wait_until_ready()
    await relay_info(f"I have been removed from a guild, making the total **{len(self.bot.guilds)}**", self.bot, short=f"I have been removed from ({guild} [{guild.id}]), making the total {len(self.bot.guilds)}", webhook=self.log_join, logger=self.logger)

  @commands.Cog.listener()
  async def on_message_edit(self, before, after):
    if after.author.bot or before.content == after.content:
      return
    await self.bot.process_commands(after)

  @commands.Cog.listener()
  async def on_command_completion(self, ctx: "MyContext"):
    self.logger.debug(f"Finished Command: {ctx.message.clean_content.encode('unicode_escape')}")

  @commands.Cog.listener()
  async def on_slash_command(self, ctx):
    self.logger.info(f"Slash Command: {ctx.command} {ctx.kwargs}")

  # @commands.Cog.listener()
  # async def on_slash_command_error(self, ctx: SlashContext, ex):
  #   print(ex)
  #   if not ctx.responded:
  #     if ctx._deffered_hidden or not ctx.deferred:
  #       await ctx.send(hidden=True, content=str(ex) or "An error has occured, try again later.")
  #     else:
  #       await ctx.send(embed=embed(title=str(ex) or "An error has occured, try again later.", color=MessageColors.ERROR))
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
      self.logger.info(f"Interaction: {interaction.data.get('custom_id','No ID')} {interaction.type}")

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
  #       await ctx.send(embed=embed(title=str(ex) or "An error has occured, try again later.", color=MessageColors.ERROR))
  #   if not isinstance(ex, (
  #           discord.NotFound,
  #           commands.CheckFailure,
  #           commands.MissingPermissions,
  #           commands.BotMissingPermissions,
  #           commands.NoPrivateMessage,
  #           commands.MaxConcurrencyReached)) and (not hasattr(ex, "log") or (hasattr(ex, "log") and ex.log is True)):
  #     raise ex

  async def process_commands(self, message):
    ctx = await self.bot.get_context(message, cls=MyContext)

    if ctx.command is None:
      return

    if ctx.command.cog_name not in ("Dev", "Config"):
      if ctx.author.id in self.bot.blacklist:
        return

      if ctx.guild is not None and ctx.guild.id in self.bot.blacklist:
        return

      if ctx.guild is not None:
        config = await self.get_guild_config(ctx.guild.id)
        if config is not None:
          if ctx.command.name in config.disabled_commands:
            return

          if config.bot_channel is not None and ctx.channel.id != config.bot_channel:
            if ctx.command.name in config.restricted_commands and not ctx.author.guild_permissions.manage_guild:
              ctx.to_bot_channel = config.bot_channel

    bucket = self.spam_control.get_bucket(message)
    current = message.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()
    retry_after = bucket.update_rate_limit(current)
    author_id = message.author.id

    super_bucket = self.super_spam_control.get_bucket(message)
    super_retry_after = super_bucket.get_retry_after(current)

    if retry_after and author_id != self.bot.owner_id and author_id != 892865928520413245:
      self._auto_spam_count[author_id] += 1
      super_retry_after = super_bucket.update_rate_limit(current)
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

    await self.bot.invoke(ctx)

  def get_prefixes(self) -> [str]:
    return ["/", "!", "f!", "!f", "%", ">", "?", "-", "(", ")"]

  @cache.cache()
  async def get_guild_config(self, guild_id: int) -> typing.Optional[Config]:
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1;"
    async with self.bot.db.pool.acquire(timeout=300.0) as conn:
      record = await conn.fetchrow(query, str(guild_id))
      self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
      if record is not None:
        return await Config.from_record(record, self.bot)
      return None

  async def fetch_user_tier(self, user: discord.User):
    if user.id == self.bot.owner_id:
      return config.PremiumTiers.tier_4
    if user is not None:
      member = await self.bot.get_or_fetch_member(self.bot.get_guild(config.support_server_id), user.id)
      if member is None:
        raise exceptions.NotInSupportServer()
      roles = [role.id for role in member.roles]
      if config.patreon_supporting_role not in roles:
        raise exceptions.NotSupporter()
      # role = [role for role in roles if role in config.premium_roles.values()]
      # something = list(config.premium_roles.values())[::2]
      available_tiers_roles = [tier for tier in config.PremiumTiers.roles if tier != 843941723041300480]
      available_tiers_roles = available_tiers_roles[::2]
      x, final_tier = 0, None
      for tier in available_tiers_roles:
        if tier in [role.id for role in member.roles]:
          final_tier = available_tiers_roles.index(tier)
          final_tier = list(config.premium_tiers)[final_tier + 1]
        x += 1
      return final_tier if final_tier is not None else None

  @discord.utils.cached_property
  def log_chat(self) -> CustomWebhook:
    return CustomWebhook.partial(os.environ.get("WEBHOOKCHATID"), os.environ.get("WEBHOOKCHATTOKEN"), session=self.bot.session)

  @discord.utils.cached_property
  def log_info(self) -> CustomWebhook:
    return CustomWebhook.partial(os.environ.get("WEBHOOKINFOID"), os.environ.get("WEBHOOKINFOTOKEN"), session=self.bot.session)

  @discord.utils.cached_property
  def log_errors(self) -> CustomWebhook:
    return CustomWebhook.partial(os.environ.get("WEBHOOKERRORSID"), os.environ.get("WEBHOOKERRORSTOKEN"), session=self.bot.session)

  @discord.utils.cached_property
  def log_join(self) -> CustomWebhook:
    return CustomWebhook.partial(os.environ.get("WEBHOOKJOINID"), os.environ.get("WEBHOOKJOINTOKEN"), session=self.bot.session)

  async def log_spammer(self, ctx, message, retry_after, *, notify=False):
    guild_id = getattr(ctx.guild, "id", None)
    self.logger.warning(f"Spamming: {{User: {message.author.id}, Guild: {guild_id}, Retry: {retry_after}}}")

  @commands.Cog.listener()
  async def on_command_error(self, ctx: "MyContext", error):
    if hasattr(ctx.command, 'on_error'):
      return

    ignored = (commands.CommandNotFound, commands.NotOwner, )
    wave_errors = (wavelink_errors.LoadTrackError, wavelink_errors.WavelinkError,)
    just_send = (commands.DisabledCommand, commands.BotMissingPermissions, commands.MissingPermissions, commands.RoleNotFound, asyncio.TimeoutError, commands.BadArgument)
    error = getattr(error, 'original', error)

    if isinstance(error, (*ignored, *wave_errors)) or (hasattr(error, "log") and error.log is False):
      return

    if isinstance(error, just_send):
      await ctx.send(embed=embed(title=error, color=MessageColors.ERROR))
    elif isinstance(error, (commands.MissingRequiredArgument, commands.TooManyArguments)):
      await ctx.send_help(ctx.command)
    elif isinstance(error, commands.CommandOnCooldown):
      retry_after = discord.utils.utcnow() + datetime.timedelta(seconds=error.retry_after)
      await ctx.send(embed=embed(title=f"This command is on a cooldown, and will be available <t:{int(retry_after.timestamp())}:R>", color=MessageColors.ERROR))
    elif isinstance(error, (exceptions.RequiredTier, exceptions.NotInSupportServer)):
      await ctx.send(embed=embed(title=error, color=MessageColors.ERROR))
    elif isinstance(error, commands.NoPrivateMessage):
      await ctx.send(embed=embed(title="This command does not work in non-server text channels", color=MessageColors.ERROR))
    elif isinstance(error, commands.CommandInvokeError):
      original = error.original
      if not isinstance(original, discord.HTTPException):
        print(f"In {ctx.command.qualified_name}:", file=sys.stderr)
        traceback.print_tb(original.__traceback__)
        self.logger.error(f"{original.__class__.__name__}: {original}", sys.stderr.readline)
    else:
      self.logger.error('Ignoring exception in command {}:'.format(ctx.command), exc_info=(type(error), error, error.__traceback__))
      if not self.bot.prod and not self.bot.canary:
        return
      try:
        await self.log_errors.safe_send(username=self.bot.user.name, avatar_url=self.bot.user.display_avatar.url, content=f"Ignoring exception in command {ctx.command}:\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}")
      except Exception as e:
        self.logger.error(f"ERROR while ignoring exception in command {ctx.command}: {e}")
      else:
        self.logger.info("ERROR sent")

  async def on_error(self, event: str, *args, **kwargs):
    trace = traceback.format_exc()
    self.logger.error(f"ERROR in {event}: ", exc_info=trace)
    if not self.bot.prod and not self.bot.canary:
      return
    try:
      await self.log_errors.safe_send(username=self.bot.user.name, avatar_url=self.bot.user.display_avatar.url, content=f"```\nERROR in {event}: \n{trace}\n```")
    except Exception as e:
      self.logger.error(f"ERROR while logging {event}: {e}")
    else:
      self.logger.info("ERROR sent")


def setup(bot):
  bot.add_cog(Log(bot))
