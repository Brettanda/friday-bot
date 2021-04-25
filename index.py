import asyncio
import logging
import os
import sys
import traceback
import json

import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from dotenv import load_dotenv

# from chatml import queryGen
# from chatml import queryIntents
# from cogs.cleanup import get_delete_time
from cogs.help import cmd_help
from functions import (MessageColors, embed, exceptions,
                       relay_info)
from functions.mysql_connection import mydb_connect, query

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(name)s:%(levelname)-8s%(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
    filemode="w",
    filename="logging.log"
)

load_dotenv()
TOKEN = os.environ.get('TOKENTEST')


# slash = SlashCommand(Friday,sync_on_cog_reload=True,sync_commands=True)

songqueue = {}
dead_nodes_sent = False
restartPending = False

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "", "config.json")) as f:
  config = json.load(f)


class MyContext(commands.Context):
  async def reply(self, content=None, **kwargs):
    ignore_coms = ["log", "help", "meme", "issue", "reactionrole", "minesweeper", "poll", "confirm"]
    if not hasattr(kwargs, "delete_after") and self.command.name not in ignore_coms:
      delete = self.bot.get_guild_delete_commands(self.message.guild)
      delete = delete if delete is not None and delete != 0 else None
      if delete is not None:
        kwargs.update({"delete_after": delete})
        await self.message.delete(delay=delete)
    if not hasattr(kwargs, "mention_author"):
      kwargs.update({"mention_author": False})
    try:
      return await self.message.reply(content, **kwargs)
    except discord.Forbidden as e:
      if "Cannot reply without permission" in str(e):
        try:
          return await self.message.channel.send(content, **kwargs)
        except Exception:
          pass
      elif "Missing Permissions" in str(e):
        pass
      else:
        raise e
    except discord.HTTPException as e:
      if "Unknown message" in str(e):
        try:
          return await self.message.channel.send(content, **kwargs)
        except Exception:
          pass
      else:
        raise e


class Friday(commands.AutoShardedBot):
  def __init__(self):
    intents = discord.Intents(
        guilds=True,
        voice_states=True,
        messages=True,
        reactions=True,
    )
    # Members intent required for giving roles appon a member
    # joining a guild, and for reaction roles that will come soon
    # intents.members = True
    allowed_mentions = discord.AllowedMentions(roles=True, everyone=False, users=True)
    super().__init__(
        # command_prefix=query_prefix or "!",
        command_prefix=self.get_guild_prefix or "!",
        strip_after_prefix=True,
        case_insensitive=True,
        intents=intents,
        owner_id=215227961048170496,
        description=config["description"],
        fetch_offline_members=False,
        allowed_mentions=allowed_mentions,
        heartbeat_timeout=150.0
    )

    self.restartPending = restartPending
    self.slash = SlashCommand(self, sync_on_cog_reload=True, sync_commands=True, override_type=True)
    self.prod = True if len(sys.argv) > 1 and (sys.argv[1] == "--prod" or sys.argv[1] == "--production") else False

    # self.spam_control = commands.CooldownMapping.from_cooldown(10, 12.0, commands.BucketType.channel)

    self.saved_guilds = {}

    for com in os.listdir("./cogs"):
      if com.endswith(".py"):
        try:
          self.load_extension(f"cogs.{com[:-3]}")
        except Exception:
          print(f"Failed to load extention {com}", file=sys.stderr)
          logging.error(f"Failed to load extention {com} {sys.stderr}")
          traceback.print_exc()

  async def get_context(self, message, *, cls=MyContext):
    return await super().get_context(message, cls=cls)

  def check(self, ctx):
    required_perms = [("send_messages", True), ("read_messages", True), ("embed_links", True), ("read_message_history", True), ("add_reactions", True), ("manage_messages", True)]
    guild = ctx.guild
    me = guild.me if guild is not None else ctx.bot.user
    permissions = ctx.channel.permissions_for(me)
    missing = [perm for perm, value in required_perms if getattr(permissions, perm) != value]

    if not missing:
      return True

    raise commands.BotMissingPermissions(missing)

  def get_guild_delete_commands(self, guild: discord.Guild = None):
    if not guild:
      return None
    delete = self.saved_guilds[guild.id]["autoDeleteMSGs"]
    return delete if delete != 0 else None

  def get_guild_prefix(self, bot, message):
    if not message.guild and message.channel:
      return "!"
    return self.saved_guilds[message.guild.id]["prefix"]

  def change_guild_prefix(self, guild_id: int, prefix: str = "!"):
    with open("guilds.json", "r") as pre:
      x = json.load(pre)

    x[guild_id]["prefix"] = prefix
    self.saved_guilds = x
    x = json.dumps(x)
    with open("guilds.json", "w") as pre:
      pre.write(x)

  def change_guild_delete(self, guild_id: int, delete: int = 0):
    with open("guilds.json", "r") as pre:
      x = json.load(pre)

    x[str(guild_id)]["autoDeleteMSGs"] = delete
    self.saved_guilds = x
    x = json.dumps(x)
    with open("guilds.json", "w") as pre:
      pre.write(x)

  def set_guild(self, guild_id: int, prefix: str = "!", autoDeleteMSG: int = 0):
    with open("guilds.json", "r") as pre:
      x = json.load(pre)
    x.update({int(guild_id): {"prefix": str(prefix), "autoDeleteMSGs": int(autoDeleteMSG)}})
    self.saved_guilds = x
    x = json.dumps(x)
    with open("guilds.json", "w") as pre:
      pre.write(x)

  def remove_guild(self, guild_id: int):
    with open("guilds.json", "r") as pre:
      x = json.load(pre)
      x.pop(guild_id, None)
    self.saved_guilds = x
    x = json.dumps(x)
    with open("guilds.json", "w") as pre:
      pre.write(x)

  def set_all_guilds(self):
    mydb = mydb_connect()
    servers = query(mydb, "SELECT id,prefix,autoDeleteMSGs,muted FROM servers")
    guilds = {}
    for guild_id, prefix, autoDeleteMSG, muted in servers:
      guilds.update({int(guild_id): {"prefix": str(prefix), "muted": True if muted == 1 else False, "autoDeleteMSGs": int(autoDeleteMSG)}})
    self.saved_guilds = guilds
    x = json.dumps(guilds)
    with open("guilds.json", "w") as pre:
      pre.write(x)

  async def on_command_error(self, ctx, error):
    slash = True if isinstance(ctx, SlashContext) else False
    if hasattr(ctx.command, 'on_error'):
      return

    # if ctx.cog:
      # if ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
      # return

    delete = self.get_guild_delete_commands(ctx.guild)
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
      await ctx.message.delete(delay=30)
    elif isinstance(error, commands.NoPrivateMessage):
      if slash:
        await ctx.send(embed=embed(title="This command does not work in non-server text channels", color=MessageColors.ERROR), delete_after=delete)
      else:
        await ctx.reply(embed=embed(title="This command does not work in non-server text channels", color=MessageColors.ERROR), delete_after=delete)
    elif isinstance(error, commands.ChannelNotFound):
      if slash:
        await ctx.send(embed=embed(title=str(error), color=MessageColors.ERROR), delete_after=delete)
      else:
        await ctx.reply(embed=embed(title=str(error), color=MessageColors.ERROR), delete_after=delete)
      # await ctx.reply(embed=embed(title="Could not find that channel",description="Make sure it is the right channel type",color=MessageColors.ERROR))
    elif isinstance(error, commands.DisabledCommand):
      if slash:
        await ctx.send(embed=embed(title=str(error) or "This command has been disabled", color=MessageColors.ERROR), delete_after=delete)
      else:
        await ctx.reply(embed=embed(title=str(error) or "This command has been disabled", color=MessageColors.ERROR), delete_after=delete)
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
          await ctx.send(embed=embed(title=f"{error}", color=MessageColors.ERROR), delete_after=delete)
        else:
          await ctx.reply(embed=embed(title=f"{error}", color=MessageColors.ERROR), delete_after=delete)
      except discord.Forbidden:
        try:
          if slash:
            await ctx.send(f"{error}", delete_after=delete)
          else:
            await ctx.reply(f"{error}", delete_after=delete)
        except discord.Forbidden:
          logging.warning("well guess i just can't respond then")
    else:
      try:
        if slash:
          await ctx.send(embed=embed(title=f"{error}", color=MessageColors.ERROR), delete_after=delete)
        else:
          await ctx.reply(embed=embed(title=f"{error}", color=MessageColors.ERROR), delete_after=delete)
      except discord.Forbidden:
        try:
          if slash:
            await ctx.send(f"{error}", delete_after=delete)
          else:
            await ctx.reply(f"{error}", delete_after=delete)
        except discord.Forbidden:
          print("well guess i just can't respond then")
          logging.warning("well guess i just can't respond then")
      raise error

  async def on_error(self, *args, **kwargs):
    appinfo = await self.application_info()
    owner = self.get_user(appinfo.team.owner.id)

    trace = traceback.format_exc()
    if "Missing Access" in str(trace):
      return
    if self.prod:
      try:
        await relay_info(
            f"{owner.mention if self.intents.members is True else ''}\n```bash\n{trace}```",
            self,
            short="Error sent",
            channel=713270561840824361
        )
      except discord.HTTPException:
        with open("err.log", "w") as f:
          f.write(f"{trace}")
          f.close()
          await relay_info(
              f"{owner.mention if self.intents.members is True else ''}",
              self,
              file="err.log",
              channel=713270561840824361
          )

    print(trace)
    logging.error(trace)

  # async def on_slash_command_error(self, ctx, *args, **kwargs):
  #   print("somethign")

  async def on_message(self, ctx):
    if ctx.author.bot:
      return

    await self.process_commands(ctx)


if __name__ == "__main__":
  print(f"Python version: {sys.version}")
  bot = Friday()
  if len(sys.argv) > 1:
    if sys.argv[1] == "--prod" or sys.argv[1] == "--production":
      TOKEN = os.environ.get("TOKEN")
  loop = asyncio.get_event_loop()
  try:
    loop.run_until_complete(bot.start(TOKEN, bot=True, reconnect=True))
  except KeyboardInterrupt:
    # mydb.close()
    logging.info("STOPED")
    loop.run_until_complete(bot.close())
  finally:
    loop.close()
