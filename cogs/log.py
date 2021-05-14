import logging
import aiohttp
import datetime
import discord

from discord.ext import commands
from discord_slash import SlashContext, SlashCommand
from cogs.help import cmd_help
from functions import MessageColors, embed, mydb_connect, query, relay_info, exceptions, config  # ,choosegame
import traceback

import os


logger = logging.getLogger(__name__)

# import discord_slash


# with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.json')) as f:
#   config = json.load(f)

# def is_enabled(ctx):
#   if not ctx.enabled:
#     raise commands.CheckFailure("Currently I am disabled, my boss has been notified, please try again later :)")
#   return True


class Log(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.loop = bot.loop

    # self.bot.add_check(is_enabled)

    if not hasattr(self.bot, "session"):
      self.bot.session = aiohttp.ClientSession(loop=self.loop)

    if not hasattr(self.bot, "spam_control"):
      self.bot.spam_control = commands.CooldownMapping.from_cooldown(8, 15.0, commands.BucketType.user)

    if not hasattr(self.bot, "slash"):
      self.bot.slash = SlashCommand(self.bot, sync_on_cog_reload=True, sync_commands=True, override_type=True)

    self.bot.process_commands = self.process_commands
    # self.bot.on_error = self.on_error

    self.bot.log_spam = self.log_spam
    self.bot.log_info = self.log_info
    self.bot.log_issues = self.log_issues
    self.bot.log_join = self.log_join
    self.bot.log_chat = self.log_chat
    self.bot.log_errors = self.log_errors
    self.bot.log_spammer = self.log_spammer

    self.bot.get_prefixes = self.get_prefixes
    self.bot.get_guild_delete_commands = self.get_guild_delete_commands
    self.bot.get_guild_prefix = self.get_guild_prefix
    self.bot.get_guild_muted = self.get_guild_muted
    self.bot.get_guild_chat_channel = self.get_guild_chat_channel

    self.bot.change_guild_prefix = self.change_guild_prefix
    self.bot.change_guild_delete = self.change_guild_delete
    self.bot.change_guild_chat_channel = self.change_guild_chat_channel

    self.bot.set_guild = self.set_guild
    self.bot.remove_guild = self.remove_guild
    # self.bot.set_all_guilds = self.set_all_guilds

    # TODO: add guilds locally after guilds have been synced with the DB

    self.bot.add_check(self.check_perms)

  def check_perms(self, ctx):
    if ctx.channel.type == discord.ChannelType.private:
      return True

    required_perms = [("send_messages", True), ("read_messages", True), ("embed_links", True), ("read_message_history", True), ("add_reactions", True)]
    guild = ctx.guild
    me = guild.me if guild is not None else ctx.bot.user
    permissions = ctx.channel.permissions_for(me)
    missing = [perm for perm, value in required_perms if getattr(permissions, perm) != value]

    if not missing:
      return True

    raise commands.BotMissingPermissions(missing)

  @commands.Cog.listener()
  async def on_shard_connect(self, shard_id):
    print(f"Shard #{shard_id} has connected")
    logger.info(f"Shard #{shard_id} has connected")

  @commands.Cog.listener()
  async def on_ready(self):
    await relay_info(f"Apart of {len(self.bot.guilds)} guilds", self.bot, logger=logger)
    mydb = mydb_connect()
    database_guilds = query(mydb, "SELECT id FROM servers")
    if len(database_guilds) != len(self.bot.guilds):
      current_guilds = []
      for guild in self.bot.guilds:
        current_guilds.append(guild.id)
      x = 0
      for guild in database_guilds:
        database_guilds[x] = guild[0]
        x = x + 1
      difference = list(set(database_guilds).symmetric_difference(set(current_guilds)))
      if len(difference) > 0:
        # now = datetime.now()
        if len(database_guilds) < len(current_guilds):
          for guild_id in difference:
            guild = self.bot.get_guild(guild_id)
            if guild is not None:
              owner = guild.owner.id if hasattr(guild, "owner") and hasattr(guild.owner, "id") else 0
              query(mydb, "INSERT INTO servers (id,owner,name,muted) VALUES (%s,%s,%s,%s)", guild.id, owner, guild.name, 0)
              if guild.system_channel is not None:
                prefix = config.defaultPrefix
                try:
                  await guild.system_channel.send(
                      f"Thank you for inviting me to your server. My name is Friday, and I like to party. I will respond to some chats directed towards me and commands. To get started with commands type `{prefix}help`.\nAn example of something I will respond to is `Hello Friday` or `{self.bot.user.name} hello`. At my current stage of development I am very chaotic, so if I do something I shouldn't have, please use the Issues channel in Friday's Development server. I am a chatbot so if i become annoying, you stop me with the command `!bot mute`. If something goes terribly wrong and you want it to stop, talk to my creator https://discord.gg/NTRuFjU"
                  )
                except discord.Forbidden:
                  pass
            else:
              print(f"HELP guild could not be found {guild_id}")
              logger.warning(f"HELP guild could not be found {guild_id}")
        elif len(database_guilds) > len(current_guilds):
          for guild_id in difference:
            query(mydb, "DELETE FROM servers WHERE id=%s", guild_id)
        else:
          print("Could not sync guilds")
          logger.warning("Could not sync guilds")
          return
        print("Synced guilds with database")
        logger.info("Synced guilds with database")
    else:
      for guild_id in database_guilds:
        guild = self.bot.get_guild(guild_id[0])
        query(mydb, "UPDATE servers SET name=%s WHERE id=%s", guild.name, guild_id[0])
    self.set_all_guilds()

  @commands.Cog.listener()
  async def on_shard_ready(self, shard_id):
    await relay_info(f"Logged on as #{shard_id} {self.bot.user}! - {self.bot.get_shard(shard_id).latency*1000:,.0f} ms", self.bot, logger=logger)

  @commands.Cog.listener()
  async def on_shard_disconnect(self, shard_id):
    await relay_info(f"Shard #{shard_id} has disconnected", self.bot, logger=logger)

  @commands.Cog.listener()
  async def on_shard_reconnect(self, shard_id):
    await relay_info(f"Shard #{shard_id} has reconnected", self.bot, logger=logger)

  @commands.Cog.listener()
  async def on_shard_resumed(self, shard_id):
    await relay_info(f"Shard #{shard_id} has resumed", self.bot, logger=logger)

  @commands.Cog.listener()
  async def on_guild_join(self, guild):
    await relay_info(f"I have joined a new guild, making the total **{len(self.bot.guilds)}**", self.bot, short=f"I have joined a new guild, making the total {len(self.bot.guilds)}", webhook=self.bot.log_join, logger=logger)
    mydb = mydb_connect()
    owner = guild.owner.id if hasattr(guild, "owner") and hasattr(guild.owner, "id") else 0
    query(mydb, "INSERT INTO servers (id,owner,name,muted) VALUES (%s,%s,%s,%s)", guild.id, owner, guild.name, 0)
    if guild.system_channel is not None:
      prefix = config.defaultPrefix
      try:
        await guild.system_channel.send(
            f"Thank you for inviting me to your server. My name is {self.bot.user.name}, and I like to party. I will respond to some chats directed towards me and commands. To get started with commands type `{prefix}help`.\nAn example of something I will respond to is `Hello {self.bot.user.name}` or `{self.bot.user.name} hello`. At my current stage of development I am very chaotic, so if I do something I shouldn't have please use send a message Issues channel in Friday's Development server. If something goes terribly wrong and you want it to stop, talk to my creator https://discord.gg/NTRuFjU\n\t- To change my prefix use the `!prefix` command.\n\t- If I start bothering people with message use the `!bot mute` command."
        )
      except discord.Forbidden:
        pass
    self.bot.set_guild(guild.id)

  @commands.Cog.listener()
  async def on_guild_remove(self, guild):
    await relay_info(f"I have been removed from a guild, making the total **{len(self.bot.guilds)}**", self.bot, short=f"I have been removed from a guild, making the total {len(self.bot.guilds)}", webhook=self.bot.log_join, logger=logger)
    mydb = mydb_connect()
    query(mydb, "DELETE FROM servers WHERE id=%s", guild.id)
    self.bot.remove_guild(guild.id)

  @commands.Cog.listener()
  async def on_member_join(self, member):
    mydb = mydb_connect()
    role_id = query(mydb, "SELECT defaultRole FROM servers WHERE id=%s", member.guild.id)
    if role_id == 0 or role_id is None or str(role_id).lower() == "null":
      return
    else:
      role = member.guild.get_role(role_id)
      if role is None:
        # await member.guild.owner.send(f"The default role that was chosen for me to add to members when they join yours server \"{member.guild.name}\" could not be found, please update the default role at https://friday-self.bot.com")
        query(mydb, "UPDATE servers SET defaultRole=NULL WHERE id=%s", member.guild.id)
      else:
        await member.add_roles(role, reason="Default Role")

  @commands.Cog.listener()
  async def on_message_edit(self, before, after):
    await self.bot.process_commands(after)

  @commands.Cog.listener()
  async def on_command(self, ctx):
    print(f"Command: {ctx.message.clean_content.encode('unicode_escape')}")
    logger.info(f"Command: {ctx.message.clean_content.encode('unicode_escape')}")

  @commands.Cog.listener()
  async def on_slash_command(self, ctx):
    print(f"Slash Command: {ctx.command} {ctx.kwargs}")
    logger.info(f"Slash Command: {ctx.command} {ctx.kwargs}")

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
        commands.MaxConcurrencyReached,
        exceptions.UserNotInVoiceChannel,
        exceptions.NoCustomSoundsFound,
        exceptions.CantSeeNewVoiceChannelType,
        exceptions.OnlySlashCommands,
        exceptions.ArgumentTooLarge)
    ):
      # print(ex)
      # logging.error(ex)
      raise ex

  async def process_commands(self, message):
    ctx = await self.bot.get_context(message)

    if ctx.command is None:
      return

    bucket = self.bot.spam_control.get_bucket(message)
    current = message.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()
    retry_after = bucket.update_rate_limit(current)
    author_id = message.author.id
    if retry_after and author_id != self.bot.owner_id:
      return await self.bot.log_spammer(ctx, message, retry_after)

    await self.bot.invoke(ctx)

  def get_prefixes(self):
    return [g["prefix"] for g in self.bot.saved_guilds.values()] + ["/", "!", "%", ">", "?"]

  def get_guild_delete_commands(self, guild: discord.Guild = None):
    if not guild:
      return None
    delete = self.bot.saved_guilds[guild.id]["autoDeleteMSGs"]
    return delete if delete != 0 else None

  def get_guild_prefix(self, bot, message):
    if not message.guild:
      return commands.when_mentioned_or(config.defaultPrefix)(bot, message)
    if message.guild.id == 707441352367013899:
      return commands.when_mentioned_or(config.defaultPrefix)(bot, message)
    return commands.when_mentioned_or(self.bot.saved_guilds[message.guild.id]["prefix"] or config.defaultPrefix)(bot, message)

  def get_guild_muted(self, guild_id: int):
    if guild_id not in [int(item.id) for item in self.bot.guilds]:
      return False
    return bool(self.bot.saved_guilds[guild_id]["muted"])

  def get_guild_chat_channel(self, guild_id: int):
    if guild_id not in [int(item.id) for item in self.bot.guilds]:
      return None
    return self.bot.saved_guilds[guild_id]["chatChannel"]

  def change_guild_prefix(self, guild_id: int, prefix: str = config.defaultPrefix):
    self.bot.saved_guilds[guild_id]["prefix"] = prefix

  def change_guild_delete(self, guild_id: int, delete: int = 0):
    self.bot.saved_guilds[guild_id]["autoDeleteMSGs"] = delete

  def change_guild_muted(self, guild_id: int, muted: bool = False):
    self.bot.saved_guilds[guild_id]["muted"] = muted

  def change_guild_chat_channel(self, guild_id: int, chatChannel: int = None):
    self.bot.saved_guilds[guild_id]["chatChannel"] = chatChannel

  def set_guild(self, guild_id: int, prefix: str = config.defaultPrefix, autoDeleteMSG: int = None, muted: bool = False, chatChannel: int = None):
    self.bot.saved_guilds.update({guild_id: {"prefix": prefix, "autoDeleteMSGs": autoDeleteMSG, "muted": muted, "chatChannel": chatChannel if chatChannel is not None else None}})

  def remove_guild(self, guild_id: int):
    self.bot.saved_guilds.pop(guild_id, None)

  def set_all_guilds(self):
    # if not hasattr(self.bot, "saved_guilds") or len(self.bot.saved_guilds) != len(self.bot.guilds):
    mydb = mydb_connect()
    servers = query(mydb, "SELECT id,prefix,autoDeleteMSGs,muted,chatChannel FROM servers")
    guilds = {}
    for guild_id, prefix, autoDeleteMSG, muted, chatChannel in servers:
      guilds.update({int(guild_id): {"prefix": str(prefix), "muted": True if muted == 1 else False, "autoDeleteMSGs": int(autoDeleteMSG), "chatChannel": int(chatChannel) if chatChannel is not None else None}})
    self.bot.saved_guilds = guilds
    return guilds

  # async def on_slash_command_error(self, ctx, *args, **kwargs):
  #   print("somethign")

  @discord.utils.cached_property
  def log_spam(self):
    return discord.Webhook.from_url(os.environ.get("WEBHOOKSPAM"), adapter=discord.AsyncWebhookAdapter(self.bot.session))

  @discord.utils.cached_property
  def log_chat(self):
    return discord.Webhook.from_url(os.environ.get("WEBHOOKCHAT"), adapter=discord.AsyncWebhookAdapter(self.bot.session))

  @discord.utils.cached_property
  def log_info(self):
    return discord.Webhook.from_url(os.environ.get("WEBHOOKINFO"), adapter=discord.AsyncWebhookAdapter(self.bot.session))

  @discord.utils.cached_property
  def log_issues(self):
    return discord.Webhook.from_url(os.environ.get("WEBHOOKISSUES"), adapter=discord.AsyncWebhookAdapter(self.bot.session))

  @discord.utils.cached_property
  def log_errors(self):
    return discord.Webhook.from_url(os.environ.get("WEBHOOKERRORS"), adapter=discord.AsyncWebhookAdapter(self.bot.session))

  @discord.utils.cached_property
  def log_join(self):
    return discord.Webhook.from_url(os.environ.get("WEBHOOKJOIN"), adapter=discord.AsyncWebhookAdapter(self.bot.session))

  async def log_spammer(self, ctx, message, retry_after, *, autoblock=False):
    guild_name = getattr(ctx.guild, "name", "No Guild/ DM Channel")
    guild_id = getattr(ctx.guild, "id", None)
    fmt = 'User %s (ID %s) in guild %r (ID %s) spamming, retry_after: %.2fs'
    logging.warning(fmt, message.author, message.author.id, guild_name, guild_id, retry_after)

    # if not autoblock:
    #   return

    # wh = self.log_spam
    # return await wh.send(
    #     username=self.user.name,
    #     avatar_url=self.user.avatar_url,
    #     embed=functions.embed(
    #         title="Auto-blocked Member",
    #         fieldstitle=["Member", "Guild Info", "Channel Info"],
    #         fieldsval=[
    #             f'{message.author} (ID: {message.author.id})',
    #             f'{guild_name} (ID: {guild_id})',
    #             f'{message.channel} (ID: {message.channel.id}'],
    #         fieldsin=[False, False, False]
    #     )
    # )

  @commands.Cog.listener()
  async def on_command_error(self, ctx, error):
    slash = True if isinstance(ctx, SlashContext) else False
    if hasattr(ctx.command, 'on_error'):
      return

    # if ctx.cog:
      # if ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
      # return

    delete = self.bot.get_guild_delete_commands(ctx.guild)
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
    elif (isinstance(error, (
                discord.Forbidden,
                discord.NotFound,
                commands.MissingPermissions,
                commands.BotMissingPermissions,
                commands.MaxConcurrencyReached,
                exceptions.UserNotInVoiceChannel,
                exceptions.NoCustomSoundsFound,
                exceptions.CantSeeNewVoiceChannelType,
                exceptions.ArgumentTooLarge)
    )):
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
