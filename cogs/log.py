import sys
import logging
import aiohttp
import datetime
import discord
import asyncio
import mysql.connector

from typing import TYPE_CHECKING
from discord.ext import commands, tasks
from discord_slash import SlashContext, SlashCommand
from cogs.help import cmd_help
from functions import MessageColors, embed, mydb_connect, query, non_coro_query, relay_info, exceptions, config  # ,choosegame
import traceback

if discord.__version__ == "1.7.3":
  from discord import AsyncWebhookAdapter
else:
  from discord.webhook.async_ import AsyncWebhookAdapter

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

    if not hasattr(self, "spam_control"):
      self.spam_control = commands.CooldownMapping.from_cooldown(5, 15.0, commands.BucketType.user)

    if not hasattr(self, "super_spam_control"):
      self.super_spam_control = commands.CooldownMapping.from_cooldown(5, 60, commands.BucketType.user)

    self.super_spam_counter = None

    if not hasattr(self, "_auto_spam_count"):
      self._auto_spam_count = Counter()

    if not hasattr(self.bot, "slash"):
      self.bot.slash = SlashCommand(self.bot, sync_on_cog_reload=True, sync_commands=True)

    if not hasattr(self, "mydb"):
      self.mydb = mydb_connect()

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

    self.check_for_mydb.start()

    self.bot.add_check(self.check_perms)

    if self.bot.cluster_idx == 0:
      non_coro_query(self.mydb, """CREATE TABLE IF NOT EXISTS servers
                                (id bigint UNIQUE NOT NULL,
                                name varchar(255) NULL,
                                tier tinytext NULL,
                                prefix varchar(5) NOT NULL DEFAULT '!',
                                patreon_user bigint NULL DEFAULT NULL,
                                muted tinyint(1) NOT NULL,
                                lang varchar(2) NULL DEFAULT NULL,
                                autoDeleteMSGs tinyint NOT NULL DEFAULT 0,
                                max_mentions int NULL DEFAULT NULL,
                                max_messages text NULL,
                                remove_invites tinyint(1) DEFAULT 0,
                                defaultRole bigint NULL DEFAULT NULL,
                                reactionRoles text NULL,
                                customJoinLeave text NULL,
                                botMasterRole bigint NULL DEFAULT NULL,
                                chatChannel bigint NULL DEFAULT NULL,
                                musicChannel bigint NULL DEFAULT NULL,
                                greeting varchar(255) NULL DEFAULT NULL,
                                customSounds longtext NULL)""")

  def check_perms(self, ctx):
    if ctx.channel.type == discord.ChannelType.private:
      return True

    required_perms = [("send_messages", True), ("read_messages", True), ("embed_links", True), ("add_reactions", True)]
    guild = ctx.guild
    me = guild.me if guild is not None else ctx.bot.user
    permissions = ctx.channel.permissions_for(me)
    missing = [perm for perm, value in required_perms if getattr(permissions, perm) != value]

    if not missing:
      return True

    raise commands.BotMissingPermissions(missing)

  @tasks.loop(seconds=10.0)
  async def check_for_mydb(self):
    try:
      self.mydb.ping(reconnect=True, attempts=10, delay=1)
    except mysql.connector.InterfaceError as e:
      await relay_info("Disconnected from MYDB", self.bot, logger=self.logger)
      raise e

  @check_for_mydb.before_loop
  async def before_check_for_mydb(self):
    await self.bot.wait_until_ready()
    while self.bot.is_closed():
      await asyncio.sleep(0.1)

  def cog_unload(self):
    self.check_for_mydb.stop()

  @commands.Cog.listener()
  async def on_shard_connect(self, shard_id):
    await relay_info(f"Shard #{shard_id} has connected", self.bot, logger=self.logger)

  @commands.Cog.listener()
  async def on_ready(self):
    #
    # FIXME: I think this could delete some of the db with more than one cluster
    #
    if self.bot.cluster_idx == 0:
      for guild in self.bot.guilds:
        await query(self.mydb, "INSERT IGNORE INTO servers (id,name,muted,lang) VALUES (%s,%s,%s,%s)", guild.id, guild.name, 0, guild.preferred_locale.split("-")[0] if guild.preferred_locale is not None else "en")

    await self.set_all_guilds()
    await relay_info(f"Apart of {len(self.bot.guilds)} guilds", self.bot, logger=self.logger)
    if not hasattr(self.bot, "uptime"):
      self.bot.uptime = datetime.datetime.utcnow()
    self.bot.ready = True

  @commands.Cog.listener()
  async def on_shard_ready(self, shard_id):
    await relay_info(f"Logged on as #{shard_id} {self.bot.user}! - {self.bot.get_shard(shard_id).latency*1000:,.0f} ms", self.bot, logger=self.logger)

  @commands.Cog.listener()
  async def on_shard_disconnect(self, shard_id):
    await relay_info(f"Shard #{shard_id} has disconnected", self.bot, logger=self.logger)

  @commands.Cog.listener()
  async def on_shard_reconnect(self, shard_id):
    await relay_info(f"Shard #{shard_id} has reconnected", self.bot, logger=self.logger)

  @commands.Cog.listener()
  async def on_shard_resumed(self, shard_id):
    await relay_info(f"Shard #{shard_id} has resumed", self.bot, logger=self.logger)

  @commands.Cog.listener()
  async def on_guild_join(self, guild: discord.Guild):
    while self.bot.is_closed():
      await asyncio.sleep(0.1)
    await relay_info(f"I have joined a new guild, making the total **{len(self.bot.guilds)}**", self.bot, short=f"I have joined a new guild, making the total {len(self.bot.guilds)}", webhook=self.log_join, logger=self.logger)
    await query(self.mydb, "INSERT IGNORE INTO servers (id,name,muted,lang) VALUES (%s,%s,%s,%s)", guild.id, guild.name, 0, guild.preferred_locale.split("-")[0])
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
          if isinstance(x, discord.TextChannel) and guild.me.permissions_in(x).send_messages
      )
    except StopIteration:
      return

    await channel.send(**config.welcome_message(self.bot))
    self.set_guild(guild.id)

  @commands.Cog.listener()
  async def on_guild_remove(self, guild):
    while self.bot.is_closed():
      await asyncio.sleep(0.1)
    await relay_info(f"I have been removed from a guild, making the total **{len(self.bot.guilds)}**", self.bot, short=f"I have been removed from a guild, making the total {len(self.bot.guilds)}", webhook=self.log_join, logger=self.logger)
    await query(self.mydb, "DELETE FROM servers WHERE id=%s", guild.id)
    self.remove_guild(guild.id)

  @commands.Cog.listener()
  async def on_message_edit(self, before, after):
    if after.author.bot or before.content == after.content:
      return
    await self.bot.process_commands(after)

  @commands.Cog.listener()
  async def on_command(self, ctx):
    self.logger.info(f"Command: {ctx.message.clean_content.encode('unicode_escape')}")

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
        commands.MissingPermissions,
        commands.BotMissingPermissions,
        commands.NoPrivateMessage,
        commands.MaxConcurrencyReached) or (hasattr(ex, "log") and ex.log is True)
    ):
      # print(ex)
      # logging.error(ex)
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

  def get_prefixes(self) -> [int]:
    return [g["prefix"] for g in self.bot.saved_guilds.values()] + ["/", "!", "%", ">", "?", "-", "(", ")"]

  async def get_guild_prefix(self, bot, message) -> str:
    if not message.guild or message.guild.id == 707441352367013899:
      return commands.when_mentioned_or(config.defaultPrefix)(bot, message)
    try:
      return commands.when_mentioned_or(self.bot.saved_guilds[message.guild.id]["prefix"] or config.defaultPrefix)(bot, message)
    except KeyError:
      await query(self.mydb, "INSERT IGNORE INTO servers (id,name,muted,lang) VALUES (%s,%s,%s,%s)", message.guild.id, message.guild.name, 0, message.guild.preferred_locale.split("-")[0])
      self.set_guild(message.guild.id)
      return commands.when_mentioned_or(self.bot.saved_guilds[message.guild.id]["prefix"] or config.defaultPrefix)(bot, message)

  def get_guild_delete_commands(self, guild: discord.Guild or int) -> int:
    try:
      if guild is not None:
        delete = self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["autoDeleteMSGs"]
        return delete if delete != 0 else None
    except KeyError:
      self.set_guild(guild)
      return delete if delete != 0 else None

  def get_guild_muted(self, guild: discord.Guild or int) -> bool:
    try:
      if guild is not None:
        if guild.id if isinstance(guild, discord.Guild) else guild not in [int(item.id) for item in self.bot.guilds]:
          return False
        return bool(self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["muted"])
    except KeyError:
      self.set_guild(guild)
      return bool(self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["muted"])

  def get_guild_chat_channel(self, guild: discord.Guild or int) -> int:
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

  def get_guild_tier(self, guild: discord.Guild or int) -> str:
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

  def get_guild_lang(self, guild: discord.Guild or int) -> str:
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

  def change_guild_prefix(self, guild: discord.Guild or int, prefix: str = config.defaultPrefix):
    if guild is not None:
      self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["prefix"] = prefix

  def change_guild_delete(self, guild: discord.Guild or int, delete: int = 0):
    if guild is not None:
      self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["autoDeleteMSGs"] = delete

  def change_guild_muted(self, guild: discord.Guild or int, muted: bool = False):
    if guild is not None:
      self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["muted"] = muted

  def change_guild_tier(self, guild: discord.Guild or int, premium: int = 0):
    if guild is not None:
      self.bot.saved_guilds.get(guild.id if isinstance(guild, discord.Guild) else guild, None)["tier"] = premium

  def change_guild_chat_channel(self, guild: discord.Guild or int, chatChannel: int = None):
    if guild is not None:
      self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["chatChannel"] = chatChannel

  def change_guild_lang(self, guild: discord.Guild or int, lang: str = None):
    if guild is not None:
      self.bot.saved_guilds[guild.id if isinstance(guild, discord.Guild) else guild]["lang"] = lang if lang is not None else guild.preferred_locale.split("-")[0] if isinstance(guild, discord.Guild) else "en"

  def set_guild(
          self,
          guild: discord.Guild or int,
          prefix: str = config.defaultPrefix,
          tier: int = 0,
          patreon_user: int = None,
          autoDeleteMSG: int = None,
          max_mentions: int = None,
          max_messages: [int] = None,
          muted: bool = False,
          chatChannel: int = None,
          lang: str = None):
    if guild is not None:
      guild = guild if isinstance(guild, discord.Guild) else self.bot.get_guild(guild)
      self.bot.saved_guilds.update(
          {guild.id if isinstance(guild, discord.Guild) else guild: {
              "prefix": prefix,
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

  def remove_guild(self, guild: discord.Guild or int):
    if guild is None:
      return False
    guild_id = guild.id if isinstance(guild, discord.Guild) else guild
    self.bot.saved_guilds.pop(guild_id, None)

  async def set_all_guilds(self):
    # if not hasattr(self.bot, "saved_guilds") or len(self.bot.saved_guilds) != len(self.bot.guilds):
    servers = await query(self.mydb,
                          "SELECT id,prefix,tier,patreon_user,autoDeleteMSGs,muted,chatChannel,lang FROM servers")
    guilds = {}
    for guild_id, prefix, tier, patreon_user, autoDeleteMSG, muted, chatChannel, lang in servers:
      guilds.update({int(guild_id): {"prefix": str(prefix), "tier": str(tier), "patreon_user": int(patreon_user) if patreon_user is not None else None, "muted": True if int(muted) == 1 else False, "autoDeleteMSGs": int(autoDeleteMSG), "chatChannel": int(chatChannel) if chatChannel is not None else None, "lang": lang}})
    self.bot.saved_guilds = guilds
    return guilds

  @discord.utils.cached_property
  def log_spam(self) -> discord.Webhook:
    if discord.__version__ == "1.7.3":
      return discord.Webhook.from_url(os.environ.get("WEBHOOKSPAM"), adapter=AsyncWebhookAdapter(aiohttp.ClientSession(loop=self.loop)))
    return discord.Webhook.from_url(os.environ.get("WEBHOOKSPAM"), session=aiohttp.ClientSession(loop=self.loop))

  @discord.utils.cached_property
  def log_chat(self) -> discord.Webhook:
    if discord.__version__ == "1.7.3":
      return discord.Webhook.from_url(os.environ.get("WEBHOOKCHAT"), adapter=AsyncWebhookAdapter(aiohttp.ClientSession(loop=self.loop)))
    return discord.Webhook.from_url(os.environ.get("WEBHOOKCHAT"), session=aiohttp.ClientSession(loop=self.loop))

  @discord.utils.cached_property
  def log_info(self) -> discord.Webhook:
    if discord.__version__ == "1.7.3":
      return discord.Webhook.from_url(os.environ.get("WEBHOOKINFO"), adapter=AsyncWebhookAdapter(aiohttp.ClientSession(loop=self.loop)))
    return discord.Webhook.from_url(os.environ.get("WEBHOOKINFO"), session=aiohttp.ClientSession(loop=self.loop))

  @discord.utils.cached_property
  def log_issues(self) -> discord.Webhook:
    if discord.__version__ == "1.7.3":
      return discord.Webhook.from_url(os.environ.get("WEBHOOKISSUES"), adapter=AsyncWebhookAdapter(aiohttp.ClientSession(loop=self.loop)))
    return discord.Webhook.from_url(os.environ.get("WEBHOOKISSUES"), session=aiohttp.ClientSession(loop=self.loop))

  @discord.utils.cached_property
  def log_errors(self) -> discord.Webhook:
    if discord.__version__ == "1.7.3":
      return discord.Webhook.from_url(os.environ.get("WEBHOOKERRORS"), adapter=AsyncWebhookAdapter(aiohttp.ClientSession(loop=self.loop)))
    return discord.Webhook.from_url(os.environ.get("WEBHOOKERRORS"), session=aiohttp.ClientSession(loop=self.loop))

  @discord.utils.cached_property
  def log_bumps(self) -> discord.Webhook:
    if discord.__version__ == "1.7.3":
      return discord.Webhook.from_url(os.environ.get("WEBHOOKBUMPS"), adapter=AsyncWebhookAdapter(aiohttp.ClientSession(loop=self.loop)))
    return discord.Webhook.from_url(os.environ.get("WEBHOOKBUMPS"), session=aiohttp.ClientSession(loop=self.loop))

  @discord.utils.cached_property
  def log_join(self) -> discord.Webhook:
    if discord.__version__ == "1.7.3":
      return discord.Webhook.from_url(os.environ.get("WEBHOOKJOIN"), adapter=AsyncWebhookAdapter(aiohttp.ClientSession(loop=self.loop)))
    return discord.Webhook.from_url(os.environ.get("WEBHOOKJOIN"), session=aiohttp.ClientSession(loop=self.loop))

  async def log_spammer(self, ctx, message, retry_after, *, notify=False):
    guild_name = getattr(ctx.guild, "name", "No Guild/ DM Channel")
    guild_id = getattr(ctx.guild, "id", None)
    fmt = 'User %s (ID %s) in guild %r (ID %s) spamming, retry_after: %.2fs'
    logging.warning(fmt, message.author, message.author.id, guild_name, guild_id, retry_after)

    if not notify:
      return

    return await self.log_spam.send(
        username=self.bot.user.name,
        avatar_url=self.bot.user.avatar_url,
        embed=embed(
            title="Spam-Control Triggered",
            fieldstitle=["Member", "Guild Info", "Channel Info"],
            fieldsval=[
                f'{message.author} (ID: {message.author.id})',
                f'{guild_name} (ID: {guild_id})',
                f'{message.channel} (ID: {message.channel.id}'],
            fieldsin=[False, False, False]
        )
    )

  @commands.Cog.listener()
  async def on_command_error(self, ctx, error):
    slash = True if isinstance(ctx, SlashContext) else False
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
