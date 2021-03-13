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


  @commands.command(name="rolecall",aliases=["rc"],description="Moves everyone with a specific role to a voicechannel. Objects that can be exluded are voicechannels,roles,and members")
  @commands.guild_only()
  @commands.has_guild_permissions(move_members = True)
  @commands.bot_has_guild_permissions(move_members = True)
  async def rolecall(self,ctx,role:discord.Role,voicechannel:typing.Optional[discord.VoiceChannel],exclusions:commands.Greedy[typing.Union[discord.Member,discord.Role,discord.VoiceChannel]]=None):
    if ctx.author.permissions_in(voicechannel).view_channel != True:
      await ctx.reply(embed=embed(title="Trying to connect to a channel you can't view 🤔",description="Im going to have to stop you right there",color=MessageColors.ERROR))
      return
    if ctx.author.permissions_in(voicechannel).connect != True:
      await ctx.reply(embed=embed(title=f"You don't have permission to connect to `{voicechannel}` so I can't complete this command",color=MessageColors.ERROR))
      return

    moved = 0
    for member in role.members:
      if (exclusions is None or (isinstance(exclusions,list) and exclusions is not None and member not in exclusions)) and member not in voicechannel.members:
        try:
          await member.move_to(voicechannel,reason=f"Role call command by {ctx.author}")
          moved += 1
        except:
          pass
    
    await ctx.reply(embed=embed(title=f"Moved {moved} members with the role `{role}` to `{voicechannel}`"))

  @commands.command(name="massmove",aliases=["move"])
  @commands.guild_only()
  @commands.has_guild_permissions(move_members = True)
  @commands.bot_has_guild_permissions(move_members = True)
  async def mass_move(self,ctx,fromChannel:typing.Optional[discord.VoiceChannel],toChannel:discord.VoiceChannel=None):
    # await ctx.guild.chunk(cache=False)
    if toChannel is None:
      toChannel = fromChannel
      fromChannel = None

    if ctx.author.permissions_in(toChannel).view_channel != True:
      await ctx.reply(embed=embed(title="Trying to connect to a channel you can't view 🤔",description="Im going to have to stop you right there",color=MessageColors.ERROR))
      return
    if ctx.author.permissions_in(toChannel).connect != True:
      await ctx.reply(embed=embed(title=f"You don't have permission to connect to `{toChannel}` so I can't complete this command",color=MessageColors.ERROR))
      return

    try:
      if fromChannel is None:
        fromChannel = ctx.author.voice.channel
    except:
      await ctx.reply(embed=embed(title="To move users from one channel to another, you need to be connected to one or specify the channel to send from.",color=MessageColors.ERROR))
      return

    memberCount = len(fromChannel.members)

    try:
      tomove = []
      for member in fromChannel.members:
        tomove.append(member.move_to(toChannel,reason=f"{ctx.author} called the move command"))
      await asyncio.gather(*tomove)
    except:
      raise
    else:
      await ctx.reply(embed=embed(title=f"Successfully moved {memberCount} members"))

  @commands.command(name="lock",description="Sets your voice channels user limit to the current number of occupants",hidden=True)
  @commands.guild_only()
  # @commands.is_owner()
  @commands.has_guild_permissions(manage_channels=True)
  @commands.bot_has_guild_permissions(manage_channels=True)
  async def lock(self,ctx,*,voicechannel:typing.Optional[discord.VoiceChannel]=None):
    # await ctx.guild.chunk(cache=False)
    if voicechannel is None:
      if ctx.author.voice is None:
        await ctx.reply(embed=embed(title="You either need to specify a voicechannel or be connected to one",color=MessageColors.ERROR))
        return
      voicechannel = ctx.author.voice.channel
    if voicechannel.user_limit > 0:
      await voicechannel.edit(user_limit=0)
      await ctx.reply(embed=embed(title=f"Unlocked `{voicechannel}`"))
    else:
      await voicechannel.edit(user_limit=len(voicechannel.members))
      await ctx.reply(embed=embed(title=f"Locked `{voicechannel}`"))

def setup(bot):
  bot.add_cog(Fun(bot))