import discord,typing,asyncio
from discord.ext import commands


from cogs.help import cmd_help

from functions import embed,MessageColors,mydb_connect,query

class ServerManage(commands.Cog):
  """Commands for managing Friday on your server"""

  def __init__(self,bot):
    self.bot = bot

  async def cog_check(self,ctx):
    if ctx.guild is None:
      raise commands.NoPrivateMessage("This command can only be used within a guild")
    return True
  
  @commands.command(name="defaultrole",hidden=True)
  @commands.is_owner()
  @commands.has_guild_permissions(manage_roles=True)
  async def _defaultrole(self,ctx,role:discord.Role):
    # TODO: Need the members intent so assign the role
    try:
      mydb = mydb_connect()
      query(mydb,f"UPDATE servers SET defaultRole=%s WHERE id=%s",role.id,ctx.guild.id)
    except:
      raise
    else:
      try:
        await ctx.reply(embed=embed(title=f"The new default role for new members is `{role}`"))
      except discord.Forbidden:
        await ctx.reply(f"The new default role for new members is `{role}`")

  @commands.command(name="prefix")
  @commands.has_guild_permissions(administrator=True)
  async def _prefix(self,ctx,new_prefix:typing.Optional[str]="!"):
    new_prefix = new_prefix.lower()
    if len(new_prefix) > 5:
      await ctx.reply(embed=embed(title="Can't set a prefix with more than 5 characters",color=MessageColors.ERROR))
      return
    try:
      mydb = mydb_connect()
      query(mydb,f"UPDATE servers SET prefix=%s WHERE id=%s",new_prefix,ctx.guild.id)
    except:
      raise
    else:
      try:
        await ctx.reply(embed=embed(title=f"My new prefix is `{new_prefix}`"))
      except discord.Forbidden:
        await ctx.reply(f"My new prefix is `{new_prefix}`")

  @commands.group(name="bot",invoke_without_command=True)
  @commands.has_guild_permissions(manage_channels=True)
  async def settings_bot(self,ctx):
    await cmd_help(ctx, ctx.command)

  @settings_bot.command(name="mute")
  @commands.has_guild_permissions(manage_channels=True)
  async def settings_bot_mute(self,ctx):
    mydb = mydb_connect()
    muted = query(mydb,"SELECT muted FROM servers WHERE id=%s",ctx.guild.id)
    if muted == 0:
      query(mydb,"UPDATE servers SET muted=%s WHERE id=%s",1,ctx.guild.id)
      await ctx.reply(embed=embed(title="I will now only respond to commands"))
    else:
      query(mydb,"UPDATE servers SET muted=%s WHERE id=%s",0,ctx.guild.id)
      await ctx.reply(embed=embed(title="I will now respond to chat message as well as commands"))

  @commands.command(name="musicchannel",description="Set the channel where I can join and play music. If none then I will join any VC",hidden=True)
  @commands.is_owner()
  @commands.has_guild_permissions(manage_channels=True)
  async def music_channel(self,ctx,voicechannel:typing.Optional[discord.VoiceChannel]=None):
    try:
      async with ctx.typing():
        mydb = mydb_connect()
        query(mydb,f"UPDATE servers SET musicChannel=%s WHERE id=%s",voicechannel.id if voicechannel is not None else None,ctx.guild.id)
    except:
      raise
    else:
      if voicechannel is None:
        await ctx.reply(embed=embed(title=f"All the voice channels are my music channels 😈 (jk)"))
      else:
        await ctx.reply(embed=embed(title=f"`{voicechannel}` is now my music channel"))

  @commands.command(name="deletecommandsafter",aliases=["deleteafter","delcoms"],description="Set the time in seconds for how long to wait before deleting command messages")
  @commands.has_guild_permissions(manage_channels=True)
  async def delete_commands_after(self,ctx,time:typing.Optional[int]=0):
    if time < 0:
      await ctx.reply(embed=embed(title="time has to be above 0"))
      return
    try:
      async with ctx.typing():
        mydb = mydb_connect()
        query(mydb,f"UPDATE servers SET autoDeleteMSGs=%s WHERE id=%s",time,ctx.guild.id)
    except:
      raise
    else:
      if time == 0:
        await ctx.reply(embed=embed(title=f"I will no longer delete command messages"))
      else:
        await ctx.reply(embed=embed(title=f"I will now delete commands after `{time}` seconds"))

  @commands.command(name="kick")
  @commands.bot_has_guild_permissions(kick_members=True)
  @commands.has_guild_permissions(kick_members=True)
  async def kick(self,ctx,members:commands.Greedy[discord.Member],*,reason:str):
    for member in members:
      if member == self.bot.user:
        try:
          await ctx.add_reaction("😢")
        except:
          pass
        return
      if member == ctx.author:
        await ctx.reply(embed=embed(title="Failed to kick yourself",color=MessageColors.ERROR))
        return
      # try:
      for member in members:
        await member.kick(reason=f"{ctx.author}: {reason}")
      # except discord.Forbidden:
        # raise commands.BotMissingPermissions(["kick_members"])
      await ctx.reply(embed=embed(title=f"Kicked `{member}` for reason `{reason}`"))
  
  @commands.command(name="ban")
  @commands.bot_has_guild_permissions(ban_members=True)
  @commands.has_guild_permissions(ban_members=True)
  async def ban(self,ctx,members:commands.Greedy[discord.Member],delete_message_days:typing.Optional[int]=0,*,reason:str):
    for member in members:
      if member == self.bot.user:
        try:
          await ctx.add_reaction("😢")
        except:
          pass
        return
      if member == ctx.author:
        await ctx.reply(embed=embed(title="Failed to ban yourself",color=MessageColors.ERROR))
        return
      # try:
      for member in members:
        await member.ban(delete_message_days=delete_message_days,reason=f"{ctx.author}: {reason}")
      # except discord.Forbidden:
        # raise commands.BotMissingPermissions(["ban_members"])
      await ctx.reply(embed=embed(title=f"Banned `{member}` for reason `{reason}`"))

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
        return await ctx.reply(embed=embed(title="You either need to specify a voicechannel or be connected to one",color=MessageColors.ERROR))
      voicechannel = ctx.author.voice.channel
    if voicechannel.user_limit > 0:
      await voicechannel.edit(user_limit=0)
      await ctx.reply(embed=embed(title=f"Unlocked `{voicechannel}`"))
    else:
      await voicechannel.edit(user_limit=len(voicechannel.members))
      await ctx.reply(embed=embed(title=f"Locked `{voicechannel}`"))

def setup(bot):
  bot.add_cog(ServerManage(bot))