import sys
import logging
import inspect
import datetime
import discord
import asyncio
# import mysql.connector

import typing
from typing import TYPE_CHECKING
from discord.ext import commands  # , tasks
from discord.ext.commands.view import StringView
from discord_slash import SlashContext, SlashCommand, ComponentContext
from cogs.help import cmd_help
from functions import MessageColors, embed, relay_info, exceptions, config, views, MyContext, FakeInteractionMessage
import traceback

from collections import Counter

import os

if TYPE_CHECKING:
  from index import Friday as Bot

GENERAL_CHANNEL_NAMES = {"welcome", "general", "lounge", "chat", "talk", "main"}

# import discord_slash


# with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.json')) as f:
#   config = json.load(f)

# def is_enabled(ctx):
#   if not ctx.enabled:
#     raise commands.CheckFailure("Currently I am disabled, my boss has been notified, please try again later :)")
#   return True

formatter = logging.Formatter("%(levelname)s:%(name)s: %(message)s")


class Log(commands.Cog):
  """Everything that is required for the bot to run but can also be reloaded without restarting the bot"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.loop = bot.loop
    self.bot.loop.create_task(self.setup())

    if not hasattr(self, "spam_control"):
      self.spam_control = commands.CooldownMapping.from_cooldown(5, 15.0, commands.BucketType.user)

    if not hasattr(self, "super_spam_control"):
      self.super_spam_control = commands.CooldownMapping.from_cooldown(5, 60, commands.BucketType.user)

    self.super_spam_counter = None

    if not hasattr(self, "_auto_spam_count"):
      self._auto_spam_count = Counter()

    if not hasattr(self.bot, "slash"):
      self.bot.slash = SlashCommand(self.bot, sync_commands=True, sync_on_cog_reload=True)

    self.bot.process_commands = self.process_commands
    # self.bot.on_error = self.on_error

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    filehandler = logging.FileHandler("logging.log", encoding="utf-8")
    filehandler.setFormatter(logging.Formatter("%(asctime)s:%(name)s:%(levelname)-8s%(message)s"))

    self.logger = logging.getLogger(f"Cluster#{self.bot.cluster_name}")
    self.logger.handlers = [handler, filehandler]
    self.logger.setLevel(logging.INFO)

    # dlog = logging.getLogger("discord")
    # dlog.handlers = [handler]
    # dlog.setLevel(logging.INFO)

    # self.check_for_mydb.start()

    self.bot.add_check(self.check_perms)

  async def setup(self) -> None:
    if self.bot.cluster_idx == 0:
      await self.bot.db.query("""CREATE TABLE IF NOT EXISTS servers
                                (id bigint PRIMARY KEY NOT NULL,
                                tier text NULL,
                                prefix varchar(5) NOT NULL DEFAULT '!',
                                patreon_user bigint NULL DEFAULT NULL,
                                muted boolean NOT NULL,
                                lang varchar(2) NULL DEFAULT NULL,
                                autoDeleteMSGs smallint NOT NULL DEFAULT 0,
                                max_mentions int NULL DEFAULT NULL,
                                max_messages text NULL,
                                remove_invites boolean DEFAULT false,
                                bot_manager bigint DEFAULT NULL,
                                persona text DEFAULT 'friday',
                                customJoinLeave text NULL,
                                botMasterRole bigint NULL DEFAULT NULL,
                                chatChannel bigint NULL DEFAULT NULL,
                                musicChannel bigint NULL DEFAULT NULL,
                                customSounds text NULL);""")

    if not hasattr(self, "bot_managers"):
      self.bot_managers = {}
      for guild_id, role_id in await self.bot.db.query("SELECT id,bot_manager FROM servers"):
        if role_id is not None:
          self.bot_managers.update({int(guild_id): int(role_id)})

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
    #
    # FIXME: I think this could delete some of the db with more than one cluster
    #
    if self.bot.cluster_idx == 0:
      current = []
      for guild in self.bot.guilds:
        current.append(guild.id)
        await self.bot.db.query("INSERT INTO servers (id,muted,lang) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING", guild.id, False, guild.preferred_locale.split("-")[0] if guild.preferred_locale is not None else "en")
      x, ticks = 1, []
      for _ in current:
        ticks.append(f"${x}")
        x += 1
      await self.bot.db.query(f"DELETE FROM servers WHERE id NOT IN ({','.join(ticks)})", *current)

    for i, p in await self.bot.db.query("SELECT id,prefix FROM servers"):
      self.bot.prefixes.update({int(i): str(p)})

  @commands.Cog.listener()
  async def on_ready(self):
    if not self.bot.views_loaded:
      # for name, view in views.__dict__.items():
      #   if isinstance(view, discord.):
      #     self.bot.add_view(view)
      self.bot.add_view(views.Links())
      self.bot.add_view(views.StopButton())
      # self.bot.add_view(views.PaginationButtons())

    await self.set_all_guilds()
    await relay_info(f"Apart of {len(self.bot.guilds)} guilds", self.bot, logger=self.logger)
    if not hasattr(self.bot, "uptime"):
      self.bot.uptime = datetime.datetime.utcnow()
    self.bot.ready = True

  @commands.Cog.listener()
  async def on_shard_ready(self, shard_id):
    await relay_info(f"Logged on as #{shard_id} {self.bot.user}! - {self.bot.get_shard(shard_id).latency*1000:,.0f} ms", self.bot, logger=self.logger)

  @commands.Cog.listener()
  async def on_disconnect(self):
    self.logger.debug("Disconnected")

  @commands.Cog.listener()
  async def on_shard_disconnect(self, shard_id):
    await relay_info(f"Shard #{shard_id} has disconnected", self.bot, logger=self.logger)

  @commands.Cog.listener()
  async def on_shard_reconnect(self, shard_id):
    await relay_info(f"Shard #{shard_id} has reconnected", self.bot, logger=self.logger)

  @commands.Cog.listener()
  async def on_resumed(self):
    self.logger.debug("Resumed")

  @commands.Cog.listener()
  async def on_shard_resumed(self, shard_id):
    await relay_info(f"Shard #{shard_id} has resumed", self.bot, logger=self.logger)

  @commands.Cog.listener()
  async def on_guild_join(self, guild: discord.Guild):
    while self.bot.is_closed():
      await asyncio.sleep(0.1)
    await self.bot.db.query("INSERT INTO servers (id,muted,lang) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING", guild.id, False, guild.preferred_locale.split("-")[0])
    priority_channels = []
    channels = []
    for channel in guild.text_channels:
      if channel == guild.system_channel or any(x in channel.name for x in GENERAL_CHANNEL_NAMES):
        priority_channels.append(channel)
      else:
        channels.append(channel)
    channels = priority_channels + channels
    try:
      channel = next(
          x
          for x in channels
          if isinstance(x, discord.TextChannel) and x.permissions_for(guild.me).send_messages
      )
    except StopIteration:
      return

    await channel.send(**config.welcome_message(self.bot))
    self.set_guild(guild.id)
    await relay_info(f"I have joined a new guild, making the total **{len(self.bot.guilds)}**", self.bot, short=f"I have joined a new guild, making the total {len(self.bot.guilds)}", webhook=self.log_join, logger=self.logger)

  @commands.Cog.listener()
  async def on_guild_remove(self, guild):
    while self.bot.is_closed():
      await asyncio.sleep(0.1)
    self.remove_guild(guild.id)
    await self.bot.db.query("DELETE FROM servers WHERE id=$1", guild.id)
    await self.bot.db.query("DELETE FROM blacklist WHERE id=$1", guild.id)
    await relay_info(f"I have been removed from a guild, making the total **{len(self.bot.guilds)}**", self.bot, short=f"I have been removed from a guild, making the total {len(self.bot.guilds)}", webhook=self.log_join, logger=self.logger)

  @commands.Cog.listener()
  async def on_message_edit(self, before, after):
    if after.author.bot or before.content == after.content:
      return
    await self.bot.process_commands(after)

  @commands.Cog.listener()
  async def on_command(self, ctx: commands.Context):
    self.logger.info(f"Command: {ctx.message.clean_content.encode('unicode_escape')}")

  @commands.Cog.listener()
  async def on_command_completion(self, ctx: commands.Context):
    self.logger.debug(f"Finished Command: {ctx.message.clean_content.encode('unicode_escape')}")

  @commands.Cog.listener()
  async def on_slash_command(self, ctx):
    self.logger.info(f"Slash Command: {ctx.command} {ctx.kwargs}")

  @commands.Cog.listener()
  async def on_slash_command_error(self, ctx: SlashContext, ex):
    if not ctx.responded:
      if ctx._deffered_hidden or not ctx.deferred:
        await ctx.send(hidden=True, content=str(ex) or "An error has occured, try again later.")
      else:
        await ctx.send(embed=embed(title=str(ex) or "An error has occured, try again later.", color=MessageColors.ERROR))
    if not isinstance(ex, (
            discord.NotFound,
            commands.CheckFailure,
            commands.MissingPermissions,
            commands.BotMissingPermissions,
            commands.NoPrivateMessage,
            commands.MaxConcurrencyReached)) and (not hasattr(ex, "log") or (hasattr(ex, "log") and ex.log is True)):
      raise ex

  async def convert_param(self, ctx: SlashContext, option, param):
    value = option["value"]
    if param.annotation != inspect.Parameter.empty:
      value = await commands.run_converters(ctx, param.annotation, value, 0)
    return value

  @commands.Cog.listener()
  async def on_interaction(self, interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.application_command:
      self.logger.info(f"Interaction: {interaction.data.get('custom_id','No ID')} {interaction.type}")

    if interaction.type == discord.InteractionType.application_command:
      command = self.bot.get_command(interaction.data["name"])

      if command is None:
        return await relay_info(f"Missing slash command: {interaction.data['name']}", self.bot, webhook=self.log_errors)

      ctx = MyContext(prefix="/", view=StringView(interaction.data["name"]), bot=self.bot, message=FakeInteractionMessage(self.bot, interaction))
      options = {option["name"]: option for option in interaction.data.get("options", {})}
      params, kwargs = [], {}
      for name, param in command.clean_params.items():
        option = options.get(name)
        if not option:
          option = param.default
        else:
          option = await self.convert_param(ctx, option, param)
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
          kwargs[name] = option
        else:
          params.append(option)

      async def fallback():
        await asyncio.sleep(2)
        if interaction.response.is_done():
          return
        try:
          await interaction.response.defer()
        except Exception:
          pass
      self.bot.loop.create_task(fallback())
      try:
        self.bot.dispatch("command", ctx)
        if await command.can_run(ctx):
          await command(ctx, *params, **kwargs)
      except Exception as e:
        self.bot.dispatch("command_error", ctx, e)

  @commands.Cog.listener()
  async def on_component_callback_error(self, ctx: ComponentContext, ex: Exception):
    if not ctx.responded:
      if ctx._deferred_hidden or not ctx.deferred:
        await ctx.send(hidden=True, content=str(ex) or "An error has occured, try again later.")
      else:
        await ctx.send(embed=embed(title=str(ex) or "An error has occured, try again later.", color=MessageColors.ERROR))
    if not isinstance(ex, (
            discord.NotFound,
            commands.CheckFailure,
            commands.MissingPermissions,
            commands.BotMissingPermissions,
            commands.NoPrivateMessage,
            commands.MaxConcurrencyReached)) and (not hasattr(ex, "log") or (hasattr(ex, "log") and ex.log is True)):
      raise ex

  async def process_commands(self, message):
    ctx = await self.bot.get_context(message)

    if ctx.command is None:
      return

    bucket = self.spam_control.get_bucket(message)
    current = message.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()
    retry_after = bucket.update_rate_limit(current)
    author_id = message.author.id

    super_bucket = self.super_spam_control.get_bucket(message)
    super_retry_after = super_bucket.get_retry_after(current)

    if retry_after and author_id != self.bot.owner_id:
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
    return [*[g for g in self.bot.prefixes.values() if g != "!"], *["/", "!", "%", ">", "?", "-", "(", ")"]]

  def get_guild_delete_commands(self, guild: typing.Union[discord.Guild, int]) -> int:
    try:
      if guild is not None:
        delete = self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["autoDeleteMSGs"]
        return delete if delete != 0 else None
    except KeyError:
      self.set_guild(guild)
      return delete if delete != 0 else None

  def get_guild_muted(self, guild: typing.Union[discord.Guild, int]) -> bool:
    try:
      if guild is not None:
        if guild.id if isinstance(guild, discord.Guild) else guild not in [int(item.id) for item in self.bot.guilds]:
          return False
        return bool(self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["muted"])
    except KeyError:
      self.set_guild(guild)
      return bool(self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["muted"])

  def get_guild_chat_channel(self, guild: typing.Union[discord.Guild, int]) -> int:
    try:
      if guild is None:
        return False
      guild_id = guild.id if isinstance(guild, discord.Guild) else guild
      if guild_id not in [int(item.id) for item in self.bot.guilds]:
        return None
      if guild.id not in self.bot.saved_guilds:
        self.set_guild(guild,)
      return self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["chatChannel"]
    except KeyError:
      self.set_guild(guild)
      return self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["chatChannel"]

  def get_guild_tier(self, guild: typing.Union[discord.Guild, int]) -> str:
    try:
      if guild is not None:
        guild = self.bot.saved_guilds.get(guild.id if isinstance(guild, discord.Guild) else guild, None)
        return guild.get("tier", "free") if guild is not None else "free"
    except KeyError:
      self.set_guild(guild)
      return guild.get("tier", "free") if guild is not None else "free"

  async def fetch_user_tier(self, user: discord.User):
    if user.id == self.bot.owner_id:
      return list(config.premium_tiers)[-1]
    if user is not None:
      member = await self.bot.get_guild(config.support_server_id).fetch_member(user.id)
      if member is None:
        raise exceptions.NotInSupportServer()
      roles = [role.id for role in member.roles]
      if config.patreon_supporting_role not in roles:
        raise exceptions.NotSupporter()
      # role = [role for role in roles if role in config.premium_roles.values()]
      # something = list(config.premium_roles.values())[::2]
      available_tiers_roles = [tier for tier in config.premium_roles.values() if tier != 843941723041300480]
      available_tiers_roles = available_tiers_roles[::2]
      x, final_tier = 0, None
      for tier in available_tiers_roles:
        if tier in [role.id for role in member.roles]:
          final_tier = available_tiers_roles.index(tier)
          final_tier = list(config.premium_tiers)[final_tier + 1]
        x += 1
      return final_tier if final_tier is not None else None

  def get_guild_lang(self, guild: typing.Union[discord.Guild, int]) -> str:
    try:
      if guild is not None:
        guild = self.bot.saved_guilds.get(guild.id if isinstance(guild, discord.Guild) else guild, None)
        lang = guild.get("lang", None) if guild is not None else None
        return lang if lang is not None else guild.preferred_locale.split("-")[0] if isinstance(guild, discord.Guild) else "en"
    except KeyError:
      self.set_guild(guild)
      return lang if lang is not None else guild.preferred_locale.split("-")[0] if isinstance(guild, discord.Guild) else "en"

  # def change_guild_attritbute(
  #         self,
  #         guild: discord.Guild or int,
  #         prefix: str = config.defaultPrefix,
  #         delete: int = None,
  #         muted: bool = False,
  #         premium: bool = False,
  #         chat_channel: int = None):
  #   if guild is None or :
  #     return False

  def change_guild_delete(self, guild: typing.Union[discord.Guild, int], delete: int = 0) -> None:
    if guild is not None:
      self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["autoDeleteMSGs"] = delete

  def change_guild_muted(self, guild: typing.Union[discord.Guild, int], muted: bool = False) -> None:
    if guild is not None:
      self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["muted"] = muted

  def change_guild_tier(self, guild: typing.Union[discord.Guild, int], premium: int = 0) -> None:
    if guild is not None:
      self.bot.saved_guilds.get(guild.id if isinstance(guild, discord.Guild) else guild, None)["tier"] = premium

  def change_guild_chat_channel(self, guild: typing.Union[discord.Guild, int], chatChannel: int = None) -> None:
    if guild is not None:
      self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["chatChannel"] = chatChannel

  def change_guild_lang(self, guild: typing.Union[discord.Guild, int], lang: str = None) -> None:
    if guild is not None:
      self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["lang"] = lang if lang is not None else guild.preferred_locale.split("-")[0] if isinstance(guild, discord.Guild) else "en"

  def set_guild(
          self,
          guild: typing.Union[discord.Guild, int],
          prefix: str = "!",
          tier: int = 0,
          patreon_user: int = None,
          autoDeleteMSG: int = None,
          max_mentions: int = None,
          max_messages: [int] = None,
          muted: bool = False,
          chatChannel: int = None,
          lang: str = None) -> None:
    if guild is not None:
      guild = guild if isinstance(guild, discord.Guild) else self.bot.get_guild(guild)
      self.bot.prefixes.update({int(guild.id): str(prefix)})
      self.bot.saved_guilds.update(
          {guild.id if isinstance(guild, discord.Guild) else guild: {
              "tier": tier,
              "patreon_user": patreon_user,
              "autoDeleteMSGs": autoDeleteMSG,
              "max_mentions": max_mentions,
              "max_messages": max_messages,
              "muted": muted,
              "chatChannel": chatChannel if chatChannel is not None else None,
              "lang": lang if lang is not None else guild.preferred_locale.split("-")[0]
          }
          })

  def remove_guild(self, guild: typing.Union[discord.Guild, int]) -> None:
    if guild is None:
      return False
    guild_id = guild.id if isinstance(guild, discord.Guild) else guild
    self.bot.saved_guilds.pop(guild_id, None)
    self.bot.prefixes.pop(guild_id, None)

  async def set_all_guilds(self) -> None:
    # if not hasattr(self.bot, "saved_guilds") or len(self.bot.saved_guilds) != len(self.bot.guilds):
    servers = await self.bot.db.query("SELECT id,tier,patreon_user,autoDeleteMSGs,chatChannel,lang FROM servers")
    guilds = {}
    for guild_id, tier, patreon_user, autoDeleteMSG, chatChannel, lang in servers:
      guilds.update({int(guild_id): {"tier": str(tier), "patreon_user": int(patreon_user) if patreon_user is not None else None, "autoDeleteMSGs": int(autoDeleteMSG), "chatChannel": int(chatChannel) if chatChannel is not None else None, "lang": lang}})
    self.bot.saved_guilds = guilds
    return guilds

  @discord.utils.cached_property
  def log_spam(self) -> discord.Webhook:
    return discord.Webhook.from_url(os.environ.get("WEBHOOKSPAM"), session=self.bot.session)

  @discord.utils.cached_property
  def log_chat(self) -> discord.Webhook:
    return discord.Webhook.from_url(os.environ.get("WEBHOOKCHAT"), session=self.bot.session)

  @discord.utils.cached_property
  def log_info(self) -> discord.Webhook:
    return discord.Webhook.from_url(os.environ.get("WEBHOOKINFO"), session=self.bot.session)

  @discord.utils.cached_property
  def log_issues(self) -> discord.Webhook:
    return discord.Webhook.from_url(os.environ.get("WEBHOOKISSUES"), session=self.bot.session)

  @discord.utils.cached_property
  def log_errors(self) -> discord.Webhook:
    return discord.Webhook.from_url(os.environ.get("WEBHOOKERRORS"), session=self.bot.session)

  @discord.utils.cached_property
  def log_bumps(self) -> discord.Webhook:
    return discord.Webhook.from_url(os.environ.get("WEBHOOKBUMPS"), session=self.bot.session)

  @discord.utils.cached_property
  def log_join(self) -> discord.Webhook:
    return discord.Webhook.from_url(os.environ.get("WEBHOOKJOIN"), session=self.bot.session)

  async def log_spammer(self, ctx, message, retry_after, *, notify=False):
    guild_id = getattr(ctx.guild, "id", None)
    self.logger.warning(f"Spamming: {{User: {message.author.id}, Guild: {guild_id}, Retry: {retry_after}}}")

  @commands.Cog.listener()
  async def on_command_error(self, ctx: commands.Context, error):
    slash = True if isinstance(ctx, SlashContext) or (hasattr(ctx, "is_interaction") and ctx.is_interaction) else False
    if hasattr(ctx.command, 'on_error'):
      return

    # if ctx.cog:
      # if ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
      # return

    delete = self.get_guild_delete_commands(ctx.guild)
    error_text = getattr(error, 'original', error)
    if isinstance(error, commands.NotOwner):
      print("Someone found a dev command")
      logging.info("Someone found a dev command")
    elif isinstance(error, commands.MissingRequiredArgument):
      await cmd_help(ctx, ctx.command, "You're missing some arguments, here is how the command should look")
    elif isinstance(error, commands.CommandNotFound):
      # await ctx.reply(embed=embed(title=f"Command `{ctx.message.content}` was not found",color=MessageColors.ERROR))
      return
    # elif isinstance(error,commands.RoleNotFound):
    #   await ctx.reply(embed=embed(title=f"{error}",color=MessageColors.ERROR))
    elif isinstance(error, commands.CommandOnCooldown):
      if slash:
        await ctx.send(embed=embed(title=f"This command is on a cooldown, please wait {error.retry_after:,.2f} sec(s)", color=MessageColors.ERROR), delete_after=30)
      else:
        await ctx.reply(embed=embed(title=f"This command is on a cooldown, please wait {error.retry_after:,.2f} sec(s)", color=MessageColors.ERROR), delete_after=30)
      if hasattr(ctx.message, "delete"):
        await ctx.message.delete(delay=30)
    elif isinstance(error, commands.NoPrivateMessage):
      if slash:
        await ctx.send(embed=embed(title="This command does not work in non-server text channels", color=MessageColors.ERROR), delete_after=delete)
      else:
        await ctx.reply(embed=embed(title="This command does not work in non-server text channels", color=MessageColors.ERROR), delete_after=delete)
    # elif isinstance(error, commands.ChannelNotFound):
    #   if slash:
    #     await ctx.send(embed=embed(title=str(error), color=MessageColors.ERROR), delete_after=delete)
    #   else:
    #     await ctx.reply(embed=embed(title=str(error), color=MessageColors.ERROR), delete_after=delete)
      # await ctx.reply(embed=embed(title="Could not find that channel",description="Make sure it is the right channel type",color=MessageColors.ERROR))
    # elif isinstance(error, commands.DisabledCommand):
    #   if slash:
    #     await ctx.send(embed=embed(title=str(error) or "This command has been disabled", color=MessageColors.ERROR), delete_after=delete)
    #   else:
    #     await ctx.reply(embed=embed(title=str(error) or "This command has been disabled", color=MessageColors.ERROR), delete_after=delete)
    elif isinstance(error, commands.TooManyArguments):
      await cmd_help(ctx, ctx.command, str(error) or "Too many arguments were passed for this command, here is how the command should look", delete_after=delete)
    # elif isinstance(error,commands.CommandError) or isinstance(error,commands.CommandInvokeError):
    #   await ctx.reply(embed=embed(title=f"{error}",color=MessageColors.ERROR))
    elif isinstance(error, (discord.Forbidden, discord.NotFound, commands.MissingPermissions, commands.BotMissingPermissions, commands.MaxConcurrencyReached)) or (hasattr(error, "log") and error.log is False):
      try:
        if slash:
          await ctx.send(embed=embed(title=f"{error_text}", color=MessageColors.ERROR), delete_after=delete)
        else:
          await ctx.reply(embed=embed(title=f"{error_text}", color=MessageColors.ERROR), delete_after=delete)
      except discord.Forbidden:
        try:
          if slash:
            await ctx.send(f"{error_text}", delete_after=delete)
          else:
            await ctx.reply(f"{error_text}", delete_after=delete)
        except discord.Forbidden:
          logging.warning("well guess i just can't respond then")
    else:
      try:
        if slash:
          await ctx.send(embed=embed(title=f"{error_text}", color=MessageColors.ERROR), delete_after=delete)
        else:
          await ctx.reply(embed=embed(title=f"{error_text}", color=MessageColors.ERROR), delete_after=delete)
      except discord.Forbidden:
        try:
          if slash:
            await ctx.send(f"{error_text}", delete_after=delete)
          else:
            await ctx.reply(f"{error_text}", delete_after=delete)
        except discord.Forbidden:
          print("well guess i just can't respond then")
          logging.warning("well guess i just can't respond then")
      raise error
      # trace = traceback.format_exception(type(error), error, error.__traceback__)
      # print(''.join(trace))
      # logging.error(''.join(trace))
      # await relay_info(
      #     f"```bash\n{''.join(trace)}```",
      #     self.bot,
      #     short="Error sent",
      #     webhook=self.log_errors
      # )

  @commands.Cog.listener()
  async def on_error(self, event, *args, **kwargs):
    trace = traceback.format_exc()
    if "Missing Access" in str(trace):
      return

    with open("err.log", "w") as f:
      f.write(trace)
      f.close()

    print(trace)
    logging.error(trace)
    await relay_info(
        f"```bash\n{trace}```",
        self.bot,
        short="Error sent",
        file="err.log",
        webhook=self.log_errors
    )


def setup(bot):
  bot.add_cog(Log(bot))
