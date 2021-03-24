import discord,asyncio,typing
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
  #   await ctx.reply(embed=embed(title=f"Successfully moved {member} to {channel}"))

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



    
    await ctx.reply(embed=embed(title=f"Moved {moved} members with the role `{role}` to `{voicechannel}`"))

            arr[y-1][x+1] += 1 # top right

            arr[y-1][x] += 1 # top center

            arr[y+1][x+1] += 1 # bottom right

    memberCount = len(fromChannel.members)

            arr[y+1][x] += 1 # bottom center

    await ctx.reply(embed=embed(title=f"{size}x{size} with {bomb_count} bombs",author_name="Minesweeper",description="||"+"||\n||".join("||||".join(self.EMOTES[cell] for cell in row) for row in arr)+"||"),delete_after=None)

def setup(bot):
  bot.add_cog(Fun(bot))