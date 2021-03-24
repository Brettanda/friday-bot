import discord,asyncio,typing,random
from discord.ext import commands

import os,sys
# sys.path.insert(1, os.path.join(sys.path[0], '..'))
from functions import embed,MessageColors

class Fun(commands.Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot
    # self.timeouter = None
    # self.timeoutCh = None

  # TODO: has no way to end this command ATM
  # TODO: can only store one user total for all of friday
  # @commands.group(name="timeout",aliases=["banish"],description="Put someone into a voice channel for a timeout",invoke_without_command=True)
  # @commands.guild_only()
  # @commands.bot_has_guild_permissions(move_members = True)
  # @commands.has_guild_permissions(move_members = True)
  # @commands.bot_has_permissions(send_messages = True, read_messages = True, embed_links = True)
  # async def timeout(self,ctx,channel:discord.VoiceChannel,member:discord.Member):
  #   self.timeouter = member
  #   self.timeoutCh = channel
  #   try:
  #     await member.move_to(channel,reason=f"{ctx.author} called the move command")
  #   except:
  #     raise
  #   await ctx.channel.send(embed=embed(title=f"Successfully moved {member} to {channel}"))

  # @timeout.command(name="stop")
  # @commands.guild_only()
  # async def timeout_stop(self,ctx):
  #   print("")

  # @commands.Cog.listener()
  # async def on_voice_state_update(self,member,before,after):
  #   if before.channel == self.timeoutCh and member == self.timeouter:
  #     await member.move_to(self.timeoutCh,reason="Bad dog, stay in your timeout room")

  # @commands.command(name="crowdcontrol",aliases=["cc"],description="Sends every back to the channel they came from if they enter a specific voicechannel")
  # @commands.guild_only()
  # @commands.bot_has_guild_permissions(move_members = True)
  # @commands.bot_has_permissions(send_messages = True, read_messages = True, embed_links = True)
  # @commands.has_guild_permissions(move_members = True)

  EMOTES = {
    "X":"💥",
    0:"0️⃣",
    1:"1️⃣",
    2:"2️⃣",
    3:"3️⃣",
    4:"4️⃣",
    5:"5️⃣",
    6:"6️⃣",
    7:"7️⃣",
    8:"8️⃣"
  }
  
  @commands.command(name="minesweeper",aliases=["ms"])
  async def mine_sweeper(self,ctx,size:typing.Optional[int]=5,bomb_count:typing.Optional[int]=6):
    """Source for this command: https://medium.com/swlh/this-is-how-to-create-a-simple-minesweeper-game-in-python-af02077a8de"""
    if size > 9:
      raise commands.BadArgument("Size cannot be larger than 9 due to the message character limit of Discord")
    if bomb_count >= size*size:
      raise commands.BadArgument("Bomb_count cannot be larger than the game board")

    arr = [[0 for row in range(size)] for column in range(size)]

    async with ctx.channel.typing():
      def get_xy():
        return random.randint(0,size-1),random.randint(0,size-1)

      for num in range(bomb_count):
        x,y = get_xy()
        while arr[y][x] == 'X':
          x,y = get_xy()
        arr[y][x] = 'X'

        if (x >=0 and x <= size-2) and (y >= 0 and y <= size-1):
          if arr[y][x+1] != 'X':
            arr[y][x+1] += 1 # center right

        if (x >=1 and x <= size-1) and (y >= 0 and y <= size-1):
          if arr[y][x-1] != 'X':
            arr[y][x-1] += 1 # center left

        if (x >= 1 and x <= size-1) and (y >= 1 and y <= size-1):
          if arr[y-1][x-1] != 'X':
            arr[y-1][x-1] += 1 # top left

        if (x >= 0 and x <= size-2) and (y >= 1 and y <= size-1):
          if arr[y-1][x+1] != 'X':
            arr[y-1][x+1] += 1 # top right
        
        if (x >= 0 and x <= size-1) and (y >= 1 and y <= size-1):
          if arr[y-1][x] != 'X':
            arr[y-1][x] += 1 # top center

        if (x >=0 and x <= size-2) and (y >= 0 and y <= size-2):
          if arr[y+1][x+1] != 'X':
            arr[y+1][x+1] += 1 # bottom right

        if (x >= 1 and x <= size-1) and (y >= 0 and y <= size-2):
          if arr[y+1][x-1] != 'X':
            arr[y+1][x-1] += 1 # bottom left

        if (x >= 0 and x <= size-1) and (y >= 0 and y <= size-2):
          if arr[y+1][x] != 'X':
            arr[y+1][x] += 1 # bottom center

    await ctx.reply(embed=embed(title=f"{size}x{size} with {bomb_count} bombs",author_name="Minesweeper",description="||"+"||\n||".join("||||".join(self.EMOTES[cell] for cell in row) for row in arr)+"||"),delete_after=None)

def setup(bot):
  bot.add_cog(Fun(bot))