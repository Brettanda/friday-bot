import discord,asyncio
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


  @commands.command(name="rolecall",description="Moves everyone with a specific role to a voicechannel after some amount of seconds")
  @commands.guild_only()
  @commands.has_guild_permissions(move_members = True)
  @commands.bot_has_guild_permissions(move_members = True)
  @commands.bot_has_permissions(send_messages = True, read_messages = True, embed_links = True)
  async def rolecall(self,ctx,role:discord.Role,voicechannel:discord.VoiceChannel,*,exclusions:discord.Member=None):
    # timeleft = time
    # message = await ctx.reply(content=f"<@&{role.id}>",embed=embed(title=f"Members of \"{role}\" will be moved to \"{voicechannel}\" in {timeleft}"))
    # message = await ctx.reply(embed=embed(title=f"Members of \"{role}\" will be moved to \"{voicechannel}\" in {timeleft}"))
    # while timeleft >= 0:
    #   await message.edit(embed=embed(title=f"Members of \"{role}\" will be moved to \"{voicechannel}\" in {timeleft}"))
    #   await asyncio.sleep(1)
    #   timeleft = timeleft - 1

    if ctx.author.permissions_in(voicechannel).view_channel != True:
      await ctx.reply(embed=embed(title="Trying to connect to a channel you can't view 🤔",description="Im going to have to stop you right there",color=MessageColors.ERROR))
      return
    if ctx.author.permissions_in(voicechannel).connect != True:
      await ctx.reply(embed=embed(title=f"You don't have permission to connect to `{voicechannel}` so I can't complete this command",color=MessageColors.ERROR))
      return

    moved = 0
    for member in role.members:
      if member not in exclusions:
        try:
          await member.move_to(voicechannel,reason=f"Role call command by {ctx.author}")
          moved += 1
        except:
          pass
    
    await ctx.reply(embed=embed(title=f"Moved {moved} members with the role `{role}` to `{voicechannel}`"))

  @commands.command(name="massmove",aliases=["move"],usage="<fromChannel:Optional> <toChannel:Required>")
  @commands.has_guild_permissions(move_members = True)
  @commands.bot_has_guild_permissions(move_members = True)
  @commands.bot_has_permissions(send_messages = True, read_messages = True, embed_links = True)
  async def mass_move(self,ctx,fromChannel:discord.VoiceChannel,toChannel:discord.VoiceChannel=None):
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
  @commands.is_owner()
  @commands.has_guild_permissions(manage_channels=True)
  @commands.bot_has_guild_permissions(manage_channels=True)
  @commands.bot_has_permissions(send_messages = True, read_messages = True, embed_links = True)
  async def lock(self,ctx,voicechannel:discord.VoiceChannel=None):
    # await ctx.guild.chunk(cache=False)
    if voicechannel is None:
      if ctx.author.voice is None:
        await ctx.reply(embed=embed(title="You either need to specify a voicechannel or be connected to one",color=MessageColors.ERROR))
        return
      voicechannel = ctx.author.voice.channel
    await voicechannel.edit(user_limit=len(voicechannel.members))
    await ctx.reply(embed=embed(title=f"Locked {voicechannel}"))

def setup(bot):
  bot.add_cog(Fun(bot))