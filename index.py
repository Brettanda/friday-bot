import os,sys,asyncio,validators,traceback,json
from datetime import datetime

from glob import glob

import discord
from dotenv import load_dotenv
from discord.ext import commands

# import logging
# logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN = os.getenv('TOKENTEST')

intents = discord.Intents.default()
intents.members = True
intents.presences = True

from functions.mysql_connection import prefix

bot = commands.AutoShardedBot(command_prefix=prefix or "!",case_insensitive=True,intents=intents)

CommandCogs = [path.split("\\")[-1][:-3] for path in glob("./cogs/*py")]

songqueue = {}
restartPending = False

bot_required_permissions = ["read_messages", "send_messages", "embed_links", "attach_files", "add_reactions", "manage_messages", "read_message_history", "move_members"]
required_permissions = ["move_members"]

from chat import queryGen
from chat import queryIntents

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '', 'config.json')) as f:
  config = json.load(f)

# from functions import embed
# embed.Embed().__init__(MessageColors)

# from functions import embed
# from functions.choosegame import ChooseGame
# choosegame = ChooseGame(bot,config).choosegame
# from functions.mysql_connection import MySQL
# mydb_connect,query = MySQL().mydb_connect,MySQL().query
# from functions import *
from functions import *

# class Friday(commands.Bot):
#   def __init__(self):
#     super().__init__(command_prefix=prefix,case_insensitive=True,owner_id=OWNER_ID)
    

# def setup(self):
for com in CommandCogs:
  # if com is not "help":
  bot.load_extension(f"cogs.{com}")
  # print(f" {com} cog loaded")
  # print("setup complete")

from cogs.help import cmd_help

async def relay_info(msg:str,file=None,short:str=None,channel:int=808594696904769546):
  if short is not None:
    print(short)
  else:
    print(msg)
  log_info = bot.get_channel(channel)
  if log_info is not None:
    if file is not None:
      thispath = os.getcwd()
      await log_info.send(msg,file=discord.File(fp=f"{thispath}\\{file}",filename="Error.txt"))
    else:
      await log_info.send(msg)
  else:
    appinfo = await bot.application_info()
    if file is not None:
      thispath = os.getcwd()
      await appinfo.owner.send(msg,file=discord.File(fp=f"{thispath}\\{file}",filename="Error.txt"))
    else:
      await appinfo.owner.send(msg)


@bot.event
async def on_command_error(ctx,error):
  # This prevents any commands with local handlers being handled here in on_command_error.
  if hasattr(ctx.command, 'on_error'):
    return

  # This prevents any cogs with an overwritten cog_command_error being handled here.
  cog = ctx.cog
  if cog:
    if cog._get_overridden_method(cog.cog_command_error) is not None:
      return

  if isinstance(error,commands.MissingRequiredArgument):
    # TODO: show the help for the specific command
    # import pprint
    # pprint.pprint(ctx)
    # await ctx.send_help(ctx.command)
    # print(bot.get_cog(ctx.command))
    await cmd_help(ctx,ctx.command,"You're missing some arguments, here is how the command should look")
    # await bot.help_command.send_command_help(ctx.command)
    # await ctx.reply(embed=embed(title=f"`{ctx.message.content}` is missing required arguments",color=MessageColors.ERROR),mention_author=False)
    return
  elif isinstance(error,commands.CommandNotFound):
    await ctx.reply(embed=embed(title=f"Command `{ctx.message.content}` was not found",color=MessageColors.ERROR),mention_author=False)
    return
  elif isinstance(error,commands.CommandOnCooldown):
    await ctx.reply(embed=embed(title=f"This command is on a cooldown, please wait {error.retry_after:,.2f} sec(s)",color=MessageColors.ERROR),mention_author=False)
    return
  elif isinstance(error,commands.NoPrivateMessage):
    await ctx.reply(embed=embed(title="This command does not work in non-server text channels",color=MessageColors.ERROR),mention_author=False)
    return
  elif isinstance(error,commands.NotOwner):
    await ctx.reply(embed=embed(title="You have found a secret command.",description="Only my developer can use this command.",color=MessageColors.ERROR),mention_author=False)
    return
  elif isinstance(error,commands.ChannelNotFound):
    await ctx.reply(embed=embed(title="Could not find that channel",description="Make sure it is the right channel type",color=MessageColors.ERROR),mention_author=False)
    return
  elif isinstance(error,commands.DisabledCommand):
    await ctx.reply(embed=embed(title="This command has been disabled",color=MessageColors.ERROR),mention_author=False)
    return
  elif isinstance(error,commands.TooManyArguments):
    await cmd_help(ctx,ctx.command,"Too many arguments were passed for this command, here is how the command should look")
    return
  elif isinstance(error,commands.MissingPermissions):
    current = ctx.channel.permissions_for(ctx.author)
    missing = []
    for perm,value in current:
      if value == False and perm.lower() in required_permissions:
        missing.append(perm)
    try:
      await ctx.reply(embed=embed(title=f"{commands.MissingPermissions(missing)}",color=MessageColors.ERROR),mention_author=False)
    except:
      await ctx.reply(f"{commands.MissingPermissions(missing)}",mention_author=False)
    return
  elif isinstance(error,commands.BotMissingPermissions):
    current = ctx.channel.permissions_for(ctx.me)
    missing = []
    for perm,value in current:
      if value == False and perm.lower() in bot_required_permissions:
        missing.append(perm)
    try:
      await ctx.reply(embed=embed(title=f'{commands.BotMissingPermissions(missing)}',color=MessageColors.ERROR),mention_author=False)
    except:
      await ctx.reply(f"{commands.BotMissingPermissions(missing)}",mention_author=False)
    return
  else:
    # print(error)
    try:
      await ctx.reply(embed=embed(title="Something has gone wrong, please try again later.",color=MessageColors.ERROR),mention_author=False)
    except:
      await ctx.reply("Something has gone wrong, please try again later.",mention_author=False)
      pass
    try:
      appinfo = await bot.application_info()
      await appinfo.owner.send(f"<@{appinfo.owner.id}>\n"+error)
    except:
      pass
    raise error

@bot.event
async def on_error(event, *args, **kwargs):
  appinfo = await bot.application_info()
  # print(traceback.format_exc())
  trace = traceback.format_exc()
  try:
    await relay_info(f"<@{appinfo.owner.id}>\n```bash\n{trace}```",short="Error sent",channel=713270561840824361)
  except discord.HTTPException:
    with open("err.log","w") as f:
      f.write(f"{trace}")
      f.close()
      await relay_info(f"<@{appinfo.owner.id}>",file="err.log",channel=713270561840824361)

  raise
  
@bot.event
async def on_shard_connect(shard_id):
  await relay_info(f"Shard #{shard_id} has connected")

@bot.event
async def on_shard_ready(shard_id):
  await relay_info(f"Logged on as #{shard_id} {bot.user}! - {bot.latency*1000:,.0f} ms")
  await relay_info(f"#{shard_id} Apart of {len(bot.guilds)} guilds")
  loop.create_task(choosegame(bot,config,1800,shard_id),name="Gaming")
  # TODO: Check for new servers, if so add them to database, and remove rows if removed from server

@bot.event
async def on_shard_disconnect(shard_id):
  await relay_info(f"Shard #{shard_id} has disconnected")

@bot.event
async def on_shard_reconnect(shard_id):
  await relay_info(f"Shard #{shard_id} has reconnected")

@bot.event
async def on_shard_resumed(shard_id):
  await relay_info(f"Shard #{shard_id} has resumed")

@bot.event
async def on_guild_join(guild):
  await relay_info(f"I have joined a new guild",713270475031183390)
  now = datetime.now()
  # current_time = now.strftime()
  mydb = mydb_connect()
  query(mydb,f"INSERT INTO servers (id,owner,name,createdAt,updatedAt) VALUES ('{guild.id}','{guild.owner_id}','{guild.name}','{now}','{now}')")
  if guild.system_channel is not None:
    prefix = "!"
    await guild.system_channel.send(
      f"Thank you for inviting me to your server. My name is Friday, and I like to party. I will respond to some chats directed towards me and commands. To get started with commands type `${prefix}help`.\nAn example of something I will respond to is `Hello Friday` or `@friday hello`. At my current stage of development I am very chaotic, so if I do something I shouldn't have please use send a message Issues channel in Friday's Development server. If something goes terribly wrong and you want it to stop, talk to my creator https://discord.gg/F8KUDwu"
    )

@bot.event
async def on_guild_remove(guild):
  await relay_info(f"I have been removed from a guild",713270475031183390)
  mydb = mydb_connect()
  query(mydb,f"DELETE FROM servers WHERE id='{guild.id}'")


@bot.event
async def on_member_join(member):
  mydb = mydb_connect()
  role_id = query(mydb,f"SELECT defaultRole FROM servers WHERE id={member.guild.id}")
  if role_id == 0 or role_id is None or str(role_id).lower() == "null":
    return
  else:
    role = member.guild.get_role(role_id)
    if role is None:
      # await member.guild.owner.send(f"The default role that was chosen for me to add to members when they join yours server \"{member.guild.name}\" could not be found, please update the default role at https://friday-bot.com")
      query(mydb,f"UPDATE servers SET defaultRole=NULL WHERE id='{member.guild.id}'")
    else:
      await member.add_roles(role,reason="Default Role")

@bot.event
async def on_message(ctx):
  if ctx.author.bot:
    return
  if ctx.activity is not None:
    return
  # Commands
  if ctx.content.startswith(str(prefix(bot,ctx)[-1])):
  # if ctx.content.startswith(ctx.command_prefix):
    # channel = ctx.channel
    print('Command: {0.content}'.format(ctx))
  else:
    # async with ctx.channel.typing():

    valid = validators.url(ctx.content)
    
    noContext = ["Title of your sex tape", "I dont want to talk to a chat bot", "The meaning of life?", "Birthday", "Memes", "Self Aware", "Soup Time", "No U", "I'm dad", "Bot discrimination"]
    lastmessages = await ctx.channel.history(limit=3).flatten()
    meinlastmessage = False
    for msg in lastmessages:
      if msg.author == bot.user:
        meinlastmessage = True
    return
    result,intent = await queryIntents.classify_local(ctx.content)
    # TODO: add a check for another bot
    # TODO: what if someone replys to friday
    if intent not in noContext and bot.user not in ctx.mentions and "friday" not in ctx.content and meinlastmessage == False and ctx.channel.type != "private":
      print("I probably should not respond")
      return
    print(f"input: {ctx.content}")
    if result is not None:
      if result == "dynamic":
        from chat.dynamicchat import dynamicchat
        await dynamicchat(ctx,bot,intent)
      else:
        await ctx.reply(result,mention_author=False)
  # else:
    # reddit = await redditlink().reddit_link(ctx)
    # if reddit is not False:
    #   print("meme")
    #   await ctx.reply(embed=reddit)
    # else:
    #   async with ctx.channel.typing():
    #     inputmsg = msg.content.split("\n")[0]
    #     print("input: {}".format(inputmsg))
    #     reply = ChatBot().generate_response(inputmsg)
    #     print("message: {}".format(reply))
    #   await ctx.reply(reply)

  await bot.process_commands(ctx)

if __name__ == "__main__":
  print(f"Python version: {sys.version}")
  if "3.8.7" not in sys.version:
    print(f"\t--The version of python that Friday was built on is 3.8.7, somethings might not work")
  if len(sys.argv) > 1:
    if sys.argv[1] == "--prod" or "--production":
      TOKEN = os.getenv("TOKEN")
      bot.load_extension("functions.dbl")
  loop = asyncio.get_event_loop()
  try:
    loop.run_until_complete(bot.start(TOKEN,bot=True,reconnect=True))
  except KeyboardInterrupt:
    # mydb.close()
    loop.run_until_complete(bot.close())
  finally:
    loop.close()