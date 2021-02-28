import os,sys,asyncio,validators,traceback,json,signal
from datetime import datetime

import discord
# from discord_slash import SlashCommand
from dotenv import load_dotenv
from discord.ext import commands

import logging
logging.basicConfig(level=logging.INFO,filename="logging.log")

load_dotenv()
TOKEN = os.getenv('TOKENTEST')

intents = discord.Intents.default()
# intents.members = True
# intents.presences = True

from functions.mysql_connection import query_prefix
from functions import ignore_guilds,dev_guilds

bot = commands.AutoShardedBot(command_prefix=query_prefix or "!",case_insensitive=True,intents=intents)
# slash = SlashCommand(bot,sync_on_cog_reload=True,sync_commands=True)

songqueue = {}
restartPending = False

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
for com in os.listdir("./cogs"):
  # if com is not "help":
  if com.endswith(".py"):
    bot.load_extension(f"cogs.{com[:-3]}")
  # print(f" {com} cog loaded")
  # print("setup complete")

from cogs.help import cmd_help
from cogs.cleanup import get_delete_time

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

  delete = await get_delete_time()
  if isinstance(error,commands.MissingRequiredArgument):
    # await ctx.send_help(ctx.command)
    # print(bot.get_cog(ctx.command))
    await cmd_help(ctx,ctx.command,"You're missing some arguments, here is how the command should look")
    # await bot.help_command.send_command_help(ctx.command)
    # await ctx.reply(embed=embed(title=f"`{ctx.message.content}` is missing required arguments",color=MessageColors.ERROR))
    return
  elif isinstance(error,commands.CommandNotFound):
    await ctx.reply(embed=embed(title=f"Command `{ctx.message.content}` was not found",color=MessageColors.ERROR))
    return
  # elif isinstance(error,commands.RoleNotFound):
  #   await ctx.reply(embed=embed(title=f"{error}",color=MessageColors.ERROR))
  #   return
  elif isinstance(error,commands.CommandOnCooldown):
    await ctx.reply(embed=embed(title=f"This command is on a cooldown, please wait {error.retry_after:,.2f} sec(s)",color=MessageColors.ERROR))
    return
  elif isinstance(error,commands.NoPrivateMessage):
    await ctx.reply(embed=embed(title="This command does not work in non-server text channels",color=MessageColors.ERROR))
    return
  elif isinstance(error,commands.NotOwner):
    await ctx.reply(embed=embed(title="You have found a secret command.",description="Only my developer can use this command.",color=MessageColors.ERROR))
    return
  elif isinstance(error,commands.ChannelNotFound):
    await ctx.reply(embed=embed(title="Could not find that channel",description="Make sure it is the right channel type",color=MessageColors.ERROR))
    return
  elif isinstance(error,commands.DisabledCommand):
    await ctx.reply(embed=embed(title="This command has been disabled",color=MessageColors.ERROR))
    return
  elif isinstance(error,commands.TooManyArguments):
    await cmd_help(ctx,ctx.command,"Too many arguments were passed for this command, here is how the command should look")
    return
  else:
    try:
      await ctx.reply(embed=embed(title=f"{error}",color=MessageColors.ERROR),delete_after=delete)
    except discord.HTTPException:
      await ctx.reply(f"{error}")
    raise error

@bot.event
async def on_error(event, *args, **kwargs):
  # await bot.get_guild(707441352367013899).chunk(cache=False)
  appinfo = await bot.application_info()
  owner = bot.get_user(appinfo.team.owner.id)

  trace = traceback.format_exc()
  try:
    await relay_info(f"{owner.mention if owner is not None else ''}\n```bash\n{trace}```",bot,short="Error sent",channel=713270561840824361)
  except discord.HTTPException:
    with open("err.log","w") as f:
      f.write(f"{trace}")
      f.close()
      await relay_info(f"{owner.mention if owner is not None else ''}",bot,file="err.log",channel=713270561840824361)

  print(trace)
  logging.error(trace)
  
@bot.event
async def on_shard_connect(shard_id):
  await bot.wait_until_ready()
  await relay_info(f"Shard #{shard_id} has connected",bot)

@bot.event
async def on_shard_ready(shard_id):
  await relay_info(f"Logged on as #{shard_id} {bot.user}! - {bot.latency*1000:,.0f} ms",bot)
  await relay_info(f"#{shard_id} Apart of {len(bot.guilds)} guilds",bot)
  loop.create_task(choosegame(bot,config,1800,shard_id),name="Gaming")
  # TODO: Check for new servers, if so add them to database, and remove rows if removed from server
  mydb = mydb_connect()
  database_guilds = query(mydb,f"SELECT id FROM servers")
  if len(database_guilds) != len(bot.guilds):
    current_guilds = []
    for guild in bot.guilds:
      current_guilds.append(guild.id)
    x = 0
    for guild in database_guilds:
      database_guilds[x] = guild[0]
      x = x + 1
    difference = list(set(database_guilds).symmetric_difference(set(current_guilds)))
    if len(difference) > 0:
      now = datetime.now()
      if len(database_guilds) < len(current_guilds):
        for guild_id in difference:
          guild = bot.get_guild(guild_id)
          owner = guild.owner.id if hasattr(guild,"owner") and hasattr(guild.owner,"id") else 0
          query(mydb,f"INSERT INTO servers (id,owner,name,createdAt,updatedAt) VALUES (%s,%s,%s,%s,%s)",guild.id,owner,guild.name,now,now)
          if guild.system_channel is not None:
            prefix = "!"
            await guild.system_channel.send(
              f"Thank you for inviting me to your server. My name is Friday, and I like to party. I will respond to some chats directed towards me and commands. To get started with commands type `{prefix}help`.\nAn example of something I will respond to is `Hello Friday` or `{bot.user.name} hello`. At my current stage of development I am very chaotic, so if I do something I shouldn't have please use send a message Issues channel in Friday's Development server. If something goes terribly wrong and you want it to stop, talk to my creator https://discord.gg/NTRuFjU"
            )
      elif len(database_guilds) > len(current_guilds):
        for guild_id in difference:
          query(mydb,f"DELETE FROM servers WHERE id=%s",guild_id)
      else:
        print("Could not sync guilds")
        logging.warn("Could not sync guilds")
        return
      print("Synced guilds with database")
      logging.info("Synced guilds with database")
  else:
  for guild_id in database_guilds:
    guild = bot.get_guild(guild_id[0])
    query(mydb,f"UPDATE servers SET name=%s WHERE id=%s",guild.name,guild_id[0])

@bot.event
async def on_shard_disconnect(shard_id):
  await relay_info(f"Shard #{shard_id} has disconnected",bot)

@bot.event
async def on_shard_reconnect(shard_id):
  await relay_info(f"Shard #{shard_id} has reconnected",bot)

@bot.event
async def on_shard_resumed(shard_id):
  await relay_info(f"Shard #{shard_id} has resumed",bot)

@bot.event
async def on_guild_join(guild):
  await relay_info("",bot,short=f"I have joined a new guild, making the total {len(bot.guilds)}",embed=embed(title=f"I have joined a new guild, making the total {len(bot.guilds)}"),channel=713270475031183390)
  now = datetime.now()
  # current_time = now.strftime()
  mydb = mydb_connect()
  owner = guild.owner.id if hasattr(guild,"owner") and hasattr(guild.owner,"id") else 0
  query(mydb,f"INSERT INTO servers (id,owner,name,createdAt,updatedAt) VALUES (%s,%s,%s,%s,%s)",guild.id,owner,guild.name,now,now)
  if guild.system_channel is not None:
    prefix = "!"
    await guild.system_channel.send(
      f"Thank you for inviting me to your server. My name is Friday, and I like to party. I will respond to some chats directed towards me and commands. To get started with commands type `{prefix}help`.\nAn example of something I will respond to is `Hello Friday` or `{bot.user.name} hello`. At my current stage of development I am very chaotic, so if I do something I shouldn't have please use send a message Issues channel in Friday's Development server. If something goes terribly wrong and you want it to stop, talk to my creator https://discord.gg/NTRuFjU"
    )

@bot.event
async def on_guild_remove(guild):
  await relay_info("",bot,short=f"I have been removed from a guild, making the total {len(bot.guilds)}",embed=embed(title=f"I have been removed from a guild, making the total {len(bot.guilds)}"),channel=713270475031183390)
  mydb = mydb_connect()
  query(mydb,f"DELETE FROM servers WHERE id=%s",guild.id)


@bot.event
async def on_member_join(member):
  mydb = mydb_connect()
  role_id = query(mydb,f"SELECT defaultRole FROM servers WHERE id=%s",member.guild.id)
  if role_id == 0 or role_id is None or str(role_id).lower() == "null":
    return
  else:
    role = member.guild.get_role(role_id)
    if role is None:
      # await member.guild.owner.send(f"The default role that was chosen for me to add to members when they join yours server \"{member.guild.name}\" could not be found, please update the default role at https://friday-bot.com")
      query(mydb,f"UPDATE servers SET defaultRole=NULL WHERE id=%s",member.guild.id)
    else:
      await member.add_roles(role,reason="Default Role")

@bot.event
async def on_message(ctx):
  if hasattr(ctx,"guild") and ctx.guild.id in ignore_guilds:
    # print("ignored guild")
    # logging.info("ignored guild")
    return
  if ctx.author.bot:
    return
  await bot.process_commands(ctx)
  if ctx.activity is not None:
    return
  # Commands
  if ctx.content.startswith(str(query_prefix(bot,ctx,True))):
  # if ctx.content.startswith(ctx.command_prefix):
    # channel = ctx.channel
    print(f'Command: {ctx.clean_content.encode("unicode_escape")}')
    logging.info(f'Command: {ctx.clean_content.encode("unicode_escape")}')
  else:
    # async with ctx.channel.typing():

    valid = validators.url(ctx.content)
    
    if "friday" in ctx.clean_content.lower() or bot.user in ctx.mentions:
      print(f"i think i should respond to this: {ctx.clean_content.lower()}")
      await relay_info("",bot,embed=embed(title="I think i should respond to this",description=f"{ctx.content}"),channel=814349008007856168)
      logging.info(f"i think i should respond to this: {ctx.clean_content.lower()}")

    if valid == True:
      return

    if len(ctx.content) > 256:
      print("message longer than 256 char")
      logging.info("message longer than 256 char")
      return

    if ctx.channel.type == "store" or ctx.channel.type == "voice" or ctx.channel.type == "category" or ctx.channel.type == "news":
      return

    if hasattr(ctx,"guild") and ctx.guild.id not in dev_guilds:
      print(f"ignored message: {ctx.clean_content}")
      logging.info(f"ignored message: {ctx.clean_content}")
      return
    noContext = ["Title of your sex tape", "I dont want to talk to a chat bot", "The meaning of life?", "Birthday", "Memes", "Self Aware", "Soup Time", "No U", "I'm dad", "Bot discrimination"]
    lastmessages = await ctx.channel.history(limit=3).flatten()
    meinlastmessage = False
    for msg in lastmessages:
      if msg.author == bot.user:
        meinlastmessage = True

    result,intent = await queryIntents.classify_local(ctx.clean_content)
    # TODO: add a check for another bot
    if intent not in noContext and bot.user not in ctx.mentions and "friday" not in ctx.content and meinlastmessage == False and ctx.channel.type != "private":
      print(f"{intent}\tI probably should not respond")
      logging.info(f"{intent}\tI probably should not respond")
      return
    print(f"input: {ctx.clean_content}")
    logging.info(f"input: {ctx.clean_content}")
    if result is not None:
      if result == "dynamic":
        from chat.dynamicchat import dynamicchat
        await dynamicchat(ctx,bot,intent)
      else:
        await ctx.reply(result)
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


if __name__ == "__main__":
  print(f"Python version: {sys.version}")
  if "3.8.7" not in sys.version:
    print(f"\t--The version of python that Friday was built on is 3.8.7, somethings might not work")
  if len(sys.argv) > 1:
    if sys.argv[1] == "--prod" or sys.argv[1] == "--production":
      TOKEN = os.getenv("TOKEN")
      bot.load_extension("functions.dbl")
  loop = asyncio.get_event_loop()
  try:
    loop.run_until_complete(bot.start(TOKEN,bot=True,reconnect=True))
  except KeyboardInterrupt:
    # mydb.close()
    loop.run_until_complete(bot.close())
    logging.info("STOPED")
  finally:
    loop.close()
