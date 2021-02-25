import discord,psutil,logging#,asyncio
from discord.ext import commands

from index import restartPending,songqueue

import os,sys
# sys.path.insert(1, os.path.join(sys.path[0], '..'))
from functions import embed,MessageColors

class Dev(commands.Cog):
  """Commands used by the developer"""

  def __init__(self,bot):
    self.bot = bot
    self.loop = bot.loop

  @commands.command(name="say",hidden=True)
  @commands.is_owner()
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def say(self,ctx,*,say:str):
    await ctx.message.delete()
    await ctx.channel.send(f"{say}")

  @commands.command(name="edit",hidden=True)
  @commands.is_owner()
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def edit(self,ctx,message:discord.Message,*,edit:str):
    await ctx.message.delete()
    await message.edit(content=edit)

  @commands.command(name="status",hidden=True)
  @commands.is_owner()
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def status(self,ctx):
    """Sends the status of the machine running Friday"""
    print("")

  @commands.command(name="restart",hidden=True)
  @commands.is_owner()
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

  @commands.command(name="mute",hidden=True)
  @commands.is_owner()
  async def mute(self,ctx):
    # TODO: Mutes this server and stops responding to commands
    print("")

  @commands.command(name="reload",hidden=True)
  @commands.is_owner()
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
  #   await ctx.reply(embed=embed(title=f"Failed to reload *{str(''.join(ctx.message.content.split(ctx.prefix+ctx.command.name+' ')))}*",color=MessageColors.ERROR),mention_author=False)
  #   raise

  @commands.command(name="update",hidden=True)
  @commands.is_owner()
  async def update(self,ctx):
    print("")

  @commands.command(name="cogs",hidden=True)
  @commands.is_owner()
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