import shutil
from discord.ext import commands

from index import restartPending,songqueue

import os
from functions import embed,MessageColors,ignore_guilds
from cogs.help import cmd_help

class Dev(commands.Cog,command_attrs=dict(hidden=True)):
  """Commands used by and for the developer"""

  def __init__(self,bot):
    self.bot = bot
    self.loop = bot.loop

  async def cog_check(self,ctx):
    is_owner = await self.bot.is_owner(ctx.author)
    if is_owner:
      return True
    raise commands.NotOwner("You do not own this bot")

  @commands.group(name="dev",invoke_without_command=True)
  async def dev(self,ctx):
    await cmd_help(ctx,ctx.command)

  @dev.command(name="say")
  async def say(self,ctx,*,say:str):
    try:
      await ctx.message.delete()
    except:
      pass
    await ctx.channel.send(f"{say}")

  @dev.command(name="edit")
  async def edit(self,ctx,message:discord.Message,*,edit:str):
    try:
      await ctx.message.delete()
    except:
      pass
    await message.edit(content=edit)

  @dev.command(name="react")
  async def react(self,ctx,message:discord.Message,*,reactions:str):
    try:
      await ctx.message.delete()
    except:
      pass
    reactions = reactions.split(" ")
    for reaction in reactions:
      await message.add_reaction(reaction)

  @dev.command(name="status")
  async def status(self,ctx):
    """Sends the status of the machine running Friday"""
    print("")

  @dev.command(name="restart")
  async def restart(self,ctx,force:bool=False):
    global restartPending,songqueue
    if restartPending == True and force == False:
      await ctx.reply(embed=embed(title="A restart is already pending"))
      return
    
    restartPending = True
    stat = await ctx.reply(embed=embed(title="Pending"))
    if len(songqueue) > 0 and force == False:
      await stat.edit(embed=embed(title=f"{len(songqueue)} guilds are playing music"))
      while len(songqueue) > 0:
        await stat.edit(embed=embed(title=f"{len(songqueue)} guilds are playing music"))
        await asyncio.sleep(1)
      await stat.edit(embed=embed(title=f"{len(songqueue)} guilds are playing music"))
    # if len(songqueue) == 0 or force == True:
    thispath = os.getcwd()
    if "\\" in thispath:
      seperator = "\\\\"
    else:
      seperator = "/"
    try:
      wait = 5
      while wait > 0:
        stat.edit(embed=embed(title=f"Restarting in {wait} seconds"))
        await asyncio.sleep(1)
        wait = wait - 1
    finally:
      await ctx.message.delete()
      await stat.delete()
      subprocess.Popen([f"{thispath}{seperator}restart.sh"], stdin=subprocess.PIPE)

  @dev.command(name="reload")
  async def reload(self,ctx,command:str):
    try:
      async with ctx.typing():
        com = self.bot.get_command(command)
        if com is not None:
          command = com.cog_name
        else:
          command = command
        self.bot.reload_extension(f"cogs.{command.lower()}")
      await ctx.reply(embed=embed(title=f"Cog *{command}* has been reloaded"))
    except:
      raise

  # @reload.error
  # async def reload_error(self,ctx,error):
  #   await ctx.reply(embed=embed(title=f"Failed to reload *{str(''.join(ctx.message.content.split(ctx.prefix+ctx.command.name+' ')))}*",color=MessageColors.ERROR))
  #   raise

  @dev.command(name="update")
  async def update(self,ctx):
    message = await ctx.reply(embed=embed(title="Updating..."))
    thispath = os.getcwd()
    if "\\" in thispath:
      seperator = "\\\\"
    else:
      seperator = "/"
    try:
      subprocess.Popen([f"{thispath}{seperator}update.sh"], stdin=subprocess.PIPE)
    except:
      raise
    else:
      await message.edit(embed=embed(title="Update complete!"))

  @dev.command(name="cogs")
  async def cogs(self,ctx):
    cogs = ", ".join(self.bot.cogs)
    await ctx.reply(embed=embed(title=f"{len(self.bot.cogs)} total cogs",description=f"{cogs}"))

  @dev.command(name="log")
  async def log(self,ctx):
    thispath = os.getcwd()
    if "\\" in thispath:
      seperator = "\\\\"
    else:
      seperator = "/"
    shutil.copy(f"{thispath}{seperator}logging.log",f"{thispath}{seperator}logging-send.log")
    await ctx.reply(file=discord.File(fp=f"{thispath}{seperator}logging-send.log",filename="logging.log"))
  

  @commands.Cog.listener()
  async def on_message(self,ctx):
    if str(ctx.channel.type) != "private" and ctx.guild.id in ignore_guilds:
        # print("ignored guild")
        # logging.info("ignored guild")
        return
    # Reacts to any message in the updates channel in the development server
    if ctx.channel.id == 744652167142441020:
      await ctx.add_reaction("♥")

    if "process.exit()" in ctx.content:
      await ctx.add_reaction("😡")
      return

def setup(bot):
  global logger
  logger = logging.getLogger(__name__)
  bot.add_cog(Dev(bot))