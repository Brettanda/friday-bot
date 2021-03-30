import os,sys,asyncio,validators,traceback,json
from datetime import datetime

import discord
from discord_slash import SlashCommand,SlashContext
from dotenv import load_dotenv
from discord.ext import commands

import logging
logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s:%(name)s:%(levelname)-8s%(message)s",
  datefmt="%y-%m-%d %H:%M:%S",
  filemode="w",
  filename="logging.log"
)

load_dotenv()
TOKEN = os.getenv('TOKENTEST')

intents = discord.Intents.default()
# Members intent required for giving roles appon a member joining a guild, and for reaction roles that will come soon
# intents.members = True

from functions.mysql_connection import query_prefix
from functions import dev_guilds

# slash = SlashCommand(bot,sync_on_cog_reload=True,sync_commands=True)

songqueue = {}
restartPending = False

# from chat import queryGen
from chat import queryIntents

from functions import embed,MessageColors,relay_info,mydb_connect,query,exceptions
from cogs.help import cmd_help
from cogs.cleanup import get_delete_time

class MyContext(commands.Context):
  async def reply(self,content=None,**kwargs):
    if not hasattr(kwargs,"delete_after") and self.command.name not in ["help","meme","issue","reactionrole","minesweeper"]:
      delete = await get_delete_time(self)
      delete = delete if delete is not None and delete != 0 else None
      if delete != None:
        kwargs.update({"delete_after":delete})
        await self.message.delete(delay=delete)
    try:
      return await self.message.reply(content,**kwargs)
    except discord.HTTPException as e:
      if "Unknown message" in str(e):
        return await self.message.channel.send(content,**kwargs)
      else:
        raise e

class Friday(commands.AutoShardedBot):
  def __init__(self):
    super(Friday,self).__init__(command_prefix=query_prefix or "!",case_insensitive=True,intents=intents)
    self.slash = SlashCommand(self,sync_on_cog_reload=True,sync_commands=True,override_type=True)

    for com in os.listdir("./cogs"):
      if com.endswith(".py"):
        self.load_extension(f"cogs.{com[:-3]}")

  async def get_context(self,message,*,cls=MyContext):
    return await super().get_context(message,cls=cls)

  def check(self,ctx):
    required_perms = [("send_messages",True),("read_messages",True),("embed_links",True),("read_message_history",True),("add_reactions",True),("manage_messages",True)]
    guild = ctx.guild
    me = guild.me if guild is not None else ctx.bot.user
    permissions = ctx.channel.permissions_for(me)
    missing = [perm for perm,value in required_perms if getattr(permissions,perm) != value]

    if not missing:
      return True

    raise commands.BotMissingPermissions(missing)

  async def on_command_error(self,ctx,error):
    if hasattr(ctx.command, 'on_error'):
      return

    if ctx.cog:
      if ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
        return

    delete = await get_delete_time(ctx)
    if isinstance(error,commands.NotOwner):
      print("Someone found a dev command")
      logging.info("Someone found a dev command")
    elif isinstance(error,commands.MissingRequiredArgument):
      await cmd_help(ctx,ctx.command,"You're missing some arguments, here is how the command should look")
    elif isinstance(error,commands.CommandNotFound):
      # await ctx.reply(embed=embed(title=f"Command `{ctx.message.content}` was not found",color=MessageColors.ERROR))
      return
    # elif isinstance(error,commands.RoleNotFound):
    #   await ctx.reply(embed=embed(title=f"{error}",color=MessageColors.ERROR))
    elif isinstance(error,commands.CommandOnCooldown):
      await ctx.reply(embed=embed(title=f"This command is on a cooldown, please wait {error.retry_after:,.2f} sec(s)",color=MessageColors.ERROR),delete_after=30)
      await ctx.delete(delay=30)
    elif isinstance(error,commands.NoPrivateMessage):
      await ctx.reply(embed=embed(title="This command does not work in non-server text channels",color=MessageColors.ERROR))
    elif isinstance(error,commands.ChannelNotFound):
      await ctx.reply(embed=embed(title="Could not find that channel",description="Make sure it is the right channel type",color=MessageColors.ERROR))
    elif isinstance(error,commands.DisabledCommand):
      await ctx.reply(embed=embed(title="This command has been disabled",color=MessageColors.ERROR))
    elif isinstance(error,commands.TooManyArguments):
      await cmd_help(ctx,ctx.command,"Too many arguments were passed for this command, here is how the command should look")
    # elif isinstance(error,commands.CommandError) or isinstance(error,commands.CommandInvokeError):
    #   await ctx.reply(embed=embed(title=f"{error}",color=MessageColors.ERROR))
    elif (
      isinstance(error,commands.MissingPermissions) or
      isinstance(error,commands.BotMissingPermissions) or
      isinstance(error,exceptions.UserNotInVoiceChannel) or
      isinstance(error,exceptions.NoCustomSoundsFound)
      ):
      try:
        await ctx.reply(embed=embed(title=f"{error}",color=MessageColors.ERROR),delete_after=delete)
      except discord.Forbidden:
        try:
          await ctx.reply(f"{error}",delete_after=delete)
        except discord.Forbidden:
          logging.warning("well guess i just can't respond then")
          pass
    else:
      try:
        await ctx.reply(embed=embed(title=f"{error}",color=MessageColors.ERROR),delete_after=delete)
      except discord.Forbidden:
        try: 
          await ctx.reply(f"{error}",delete_after=delete)
        except discord.Forbidden:
          print("well guess i just can't respond then")
          logging.warning("well guess i just can't respond then")
          pass
      raise error

  async def on_error(self,event, *args, **kwargs):
    # await bot.get_guild(707441352367013899).chunk(cache=False)
    appinfo = await bot.application_info()
    owner = bot.get_user(appinfo.team.owner.id)

    trace = traceback.format_exc()
    try:
      await relay_info(f"{owner.mention if owner is not None and bot.intents.members == True else ''}\n```bash\n{trace}```",bot,short="Error sent",channel=713270561840824361)
    except discord.HTTPException:
      with open("err.log","w") as f:
        f.write(f"{trace}")
        f.close()
        await relay_info(f"{owner.mention if owner is not None and bot.intents.members == True else ''}",bot,file="err.log",channel=713270561840824361)

    print(trace)
    logging.error(trace)

  async def on_message(self,ctx):
    if ctx.author.bot:
      return

    await self.process_commands(ctx)

if __name__ == "__main__":
  print(f"Python version: {sys.version}")
  bot = Friday()
  if len(sys.argv) > 1:
    if sys.argv[1] == "--prod" or sys.argv[1] == "--production":
      TOKEN = os.getenv("TOKEN")
      bot.load_extension("functions.dbl")
  loop = asyncio.get_event_loop()
  try:
    loop.run_until_complete(bot.start(TOKEN,bot=True,reconnect=True))
  except KeyboardInterrupt:
    # mydb.close()
    logging.info("STOPED")
    loop.run_until_complete(bot.close())
  finally:
    loop.close()
