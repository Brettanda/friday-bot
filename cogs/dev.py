import discord,psutil,logging,git
from discord.ext import commands

from index import restartPending,songqueue

import os,sys
from functions import embed,MessageColors
from cogs.help import cmd_help

class Dev(commands.Cog):
  """Commands used by the developer"""

  def __init__(self,bot):
    self.bot = bot
    self.loop = bot.loop

  @commands.group(name="dev",invoke_without_command=True,hidden=True)
  @commands.is_owner()
  async def dev(self,ctx):
    await cmd_help(ctx,ctx.command)

  @dev.command(name="say",hidden=True)
  @commands.is_owner()
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def say(self,ctx,*,say:str):
    await ctx.message.delete()
    await ctx.channel.send(f"{say}")

  @dev.command(name="edit",hidden=True)
  @commands.is_owner()
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def edit(self,ctx,message:discord.Message,*,edit:str):
    await ctx.message.delete()
    await message.edit(content=edit)

  @dev.command(name="status",hidden=True)
  @commands.is_owner()
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def status(self,ctx):
    """Sends the status of the machine running Friday"""
    print("")

  @dev.command(name="restart",hidden=True)
  @commands.is_owner()
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def restart(self,ctx):
    global restartPending,songqueue
    if restartPending == True:
      await ctx.reply(embed=embed(title="A restart is already pending"))
      return
    
    restartPending = True
    stat = await ctx.reply(embed=embed(title="Pending"))
    if len(songqueue) > 0:
      await stat.edit(embed=embed(title=f"{len(songqueue)} guilds are playing music"))
      while len(songqueue) > 0:
        await stat.edit(embed=embed(title=f"{len(songqueue)} guilds are playing music"))
      await stat.edit(embed=embed(title=f"{len(songqueue)} guilds are playing music"))
    if len(songqueue) == 0:
      p = None
      try:
        p = psutil.Process(os.getpid())
        # loop = asyncio.get_event_loop()
        await stat.edit(embed=embed(title="Restarting"))
        # self.loop.run_until_complete(await self.bot.close())
        self.loop.close()
        for handler in p.get_open_files() + p.connections():
          os.close(handler.fd)
        # os.execv(sys.argv[0], sys.argv)
        restartPending = False
      except Exception as e:
        logging.error(e)
        restartPending = True
        # raise
      python = sys.executable
      try:
        os.execl(python, python, *sys.argv)
      except KeyboardInterrupt:
        for handler in p.get_open_files() + p.connections():
          os.close(handler.fd)
        self.loop.run_until_complete(self.bot.close())
        self.loop.close()

  @dev.command(name="mute",hidden=True)
  @commands.is_owner()
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def mute(self,ctx):
    # TODO: Mutes this server and stops responding to commands
    print("")

  @dev.command(name="reload",hidden=True)
  @commands.is_owner()
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def reload(self,ctx,command:str=None):
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

  async def do_update(self):
    g = git.cmd.Git("git@github.com:Brettanda/friday-discord-python.git")
    g.fetch()

  @dev.command(name="update",hidden=True)
  @commands.is_owner()
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def update(self,ctx):
    message = await ctx.reply(embed=embed(title="Updating..."))
    await self.do_update()

  @dev.command(name="cogs",hidden=True)
  @commands.is_owner()
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def cogs(self,ctx):
    cogs = ", ".join(self.bot.cogs)
    await ctx.reply(embed=embed(title=f"{len(self.bot.cogs)} total cogs",description=f"{cogs}"))

  @commands.Cog.listener()
  async def on_message(self,ctx):
    # Reacts to any message in the updates channel in the development server
    if ctx.channel.id == 744652167142441020:
      await ctx.add_reaction("♥")

    if "process.exit()" in ctx.content:
      await ctx.add_reaction("😡")
      return

def setup(bot):
  bot.add_cog(Dev(bot))