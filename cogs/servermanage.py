import asyncio
import typing

import discord
from discord.ext import commands
from discord_slash import SlashContext, cog_ext
from discord_slash.utils.manage_commands import create_option  # ,create_choice

from cogs.help import cmd_help
from functions import MessageColors, embed, mydb_connect, query


class ServerManage(commands.Cog):
  """Commands for managing Friday on your server"""

  def __init__(self,bot):
    self.bot = bot

  def cog_check(self,ctx):
    if ctx.guild is None:
      raise commands.NoPrivateMessage("This command can only be used within a guild")
    return True

  @commands.command(name="defaultrole",hidden=True)
  @commands.is_owner()
  @commands.has_guild_permissions(manage_roles=True)
  async def _defaultrole(self,ctx,role:discord.Role):
    # TODO: Need the members intent so assign the role
    mydb = mydb_connect()
    query(mydb,"UPDATE servers SET defaultRole=%s WHERE id=%s",role.id,ctx.guild.id)
    try:
      await ctx.reply(embed=embed(title=f"The new default role for new members is `{role}`"))
    except discord.Forbidden:
      await ctx.reply(f"The new default role for new members is `{role}`")

  # @commands.command(name="mute")
  # @commands.is_owner()
  # @commands.has_guild_permissions(manage_roles=True)
  # async def mute(self,ctx,members:commands.Greedy[discord.Member]=None):
  #   if self.bot.user in members:
  #     mydb = mydb_connect()
  #     muted = query(mydb,"SELECT muted FROM servers WHERE id=%s",ctx.guild.id)
  #     if muted == 0:
  #       query(mydb,"UPDATE servers SET muted=%s WHERE id=%s",1,ctx.guild.id)
  #       await ctx.reply(embed=embed(title="I will now only respond to commands"))
  #     else:
  #       query(mydb,"UPDATE servers SET muted=%s WHERE id=%s",0,ctx.guild.id)
  #       await ctx.reply(embed=embed(title="I will now respond to chat message as well as commands"))

  @commands.command(name="prefix")
  @commands.has_guild_permissions(administrator=True)
  async def _prefix(self,ctx,new_prefix:typing.Optional[str]="!"):
    new_prefix = new_prefix.lower()
    if len(new_prefix) > 5:
      await ctx.reply(embed=embed(title="Can't set a prefix with more than 5 characters",color=MessageColors.ERROR))
      return
    mydb = mydb_connect()
    query(mydb,"UPDATE servers SET prefix=%s WHERE id=%s",new_prefix,ctx.guild.id)
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
    async with ctx.typing():
      mydb = mydb_connect()
      query(mydb,"UPDATE servers SET musicChannel=%s WHERE id=%s",voicechannel.id if voicechannel is not None else None,ctx.guild.id)
    if voicechannel is None:
      await ctx.reply(embed=embed(title="All the voice channels are my music channels 😈 (jk)"))
    else:
      await ctx.reply(embed=embed(title=f"`{voicechannel}` is now my music channel"))

  @commands.command(name="deletecommandsafter",aliases=["deleteafter","delcoms"],description="Set the time in seconds for how long to wait before deleting command messages")
  @commands.has_guild_permissions(manage_channels=True)
  async def delete_commands_after(self,ctx,time:typing.Optional[int]=0):
    if time < 0:
      await ctx.reply(embed=embed(title="time has to be above 0"))
      return
    async with ctx.typing():
      mydb = mydb_connect()
      query(mydb,"UPDATE servers SET autoDeleteMSGs=%s WHERE id=%s",time,ctx.guild.id)
    if time == 0:
      await ctx.reply(embed=embed(title="I will no longer delete command messages"))
    else:
      await ctx.reply(embed=embed(title=f"I will now delete commands after `{time}` seconds"))

  # @commands.command(name="clear",description="Deletes my messages and commands (not including the meme command)")
  # @commands.has_permissions(manage_messages = True)
  # @commands.bot_has_permissions(manage_messages = True)
  # async def clear(self,ctx,count:int):
  #   # await ctx.channel.purge(limit=count)
  #   async for message in ctx.channel.history():
  #     if message.author == self.bot.user:
  #       print("")

  @commands.command(name="kick")
  @commands.bot_has_guild_permissions(kick_members=True)
  @commands.has_guild_permissions(kick_members=True)
  async def kick(self,ctx,members:commands.Greedy[discord.Member],*,reason:str):
    for member in members:
      if self.bot.user in members:
        try:
          await ctx.add_reaction("😢")
        except:
          pass
        return
      if member == ctx.author:
        await ctx.reply(embed=embed(title="Failed to kick yourself",color=MessageColors.ERROR))
        return
      await member.kick(reason=f"{ctx.author}: {reason}")
    await ctx.reply(embed=embed(title=f"Kicked `{members.join(', ')}` for reason `{reason}`"))

  @commands.command(name="ban")
  @commands.bot_has_guild_permissions(ban_members=True)
  @commands.has_guild_permissions(ban_members=True)
  async def ban(self,ctx,members:commands.Greedy[discord.Member],delete_message_days:typing.Optional[int]=0,*,reason:str=None):
    for member in members:
      if self.bot.user in members:
        try:
          await ctx.add_reaction("😢")
        except:
          pass
        return
      if member == ctx.author:
        await ctx.reply(embed=embed(title="Failed to ban yourself",color=MessageColors.ERROR))
        return
      await member.ban(delete_message_days=delete_message_days,reason=f"{ctx.author}: {reason}")
    await ctx.reply(embed=embed(title=f"Banned `{members.join(', ')}` with `{delete_message_days}` messages deleted, for reason `{reason}`"))

  @commands.command(name="rolecall",aliases=["rc"],description="Moves everyone with a specific role to a voicechannel. Objects that can be exluded are voicechannels,roles,and members")
  @commands.guild_only()
  @commands.has_guild_permissions(move_members = True)
  @commands.bot_has_guild_permissions(move_members = True)
  async def rolecall(self,ctx,role:discord.Role,voicechannel:typing.Optional[discord.VoiceChannel],exclusions:commands.Greedy[typing.Union[discord.Member,discord.Role,discord.VoiceChannel]]=None):
    if ctx.author.permissions_in(voicechannel).view_channel is not True:
      await ctx.reply(embed=embed(title="Trying to connect to a channel you can't view 🤔",description="Im going to have to stop you right there",color=MessageColors.ERROR))
      return
    if ctx.author.permissions_in(voicechannel).connect is not True:
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
  async def norm_mass_move(self,ctx,fromChannel:typing.Optional[typing.Union[discord.VoiceChannel,discord.TextChannel,discord.StoreChannel,discord.CategoryChannel]],toChannel:typing.Optional[typing.Union[discord.VoiceChannel,discord.TextChannel,discord.StoreChannel,discord.CategoryChannel]]=None):
    post = await self.mass_move(ctx, fromChannel,toChannel)
    await ctx.reply(**post)

  @cog_ext.cog_slash(
    name="move",
    description="Move users from one voice channel to another",
    options=[
      create_option(
        "fromchannel",
        "The voice channel to move from",
        7,
        required=True
      ),
      create_option(
        "tochannel",
        "The voice channel to move to",
        7,
        required=False
      )
    ],
    guild_ids=[243159711237537802,805579185879121940]
  )
  @commands.guild_only()
  # @commands.has_guild_permissions(move_members = True)
  # @commands.bot_has_guild_permissions(move_members = True)
  async def slash_mass_move(self,ctx,fromChannel,toChannel=None):
    await ctx.defer(True)
    post = await self.mass_move(ctx, fromChannel,toChannel)
    await ctx.send(hidden=True,**post)

  async def mass_move(self,ctx,fromChannel,toChannel=None):
    # await ctx.guild.chunk(cache=False)
    if toChannel is None:
      toChannel = fromChannel
      fromChannel = None

    if (fromChannel is not None and not isinstance(fromChannel, discord.VoiceChannel)) or (toChannel is not None and not isinstance(toChannel, discord.VoiceChannel)):
      if isinstance(ctx, SlashContext):
        return dict(content="Please only select voice channels for moving")
      return dict(embed=embed(title="Please only select voice channels for moving"))

    if ctx.author.permissions_in(toChannel).view_channel is not True:
      if isinstance(ctx, SlashContext):
        return dict(content="Trying to connect to a channel you can't view 🤔\nIm going to have to stop you right there")
      return dict(embed=embed(title="Trying to connect to a channel you can't view 🤔",description="Im going to have to stop you right there",color=MessageColors.ERROR))
    if ctx.author.permissions_in(toChannel).connect is not True:
      if isinstance(ctx, SlashContext):
        return dict(content=f"You don't have permission to connect to `{toChannel}` so I can't complete this command")
      return dict(embed=embed(title=f"You don't have permission to connect to `{toChannel}` so I can't complete this command",color=MessageColors.ERROR))

    try:
      if fromChannel is None:
        fromChannel = ctx.author.voice.channel
    except:
      if isinstance(ctx, SlashContext):
        return dict(content="To move users from one channel to another, you need to be connected to one or specify the channel to send from.")
      return dict(embed=embed(title="To move users from one channel to another, you need to be connected to one or specify the channel to send from.",color=MessageColors.ERROR))

    memberCount = len(fromChannel.members)

    tomove = []
    for member in fromChannel.members:
      tomove.append(member.move_to(toChannel,reason=f"{ctx.author} called the move command"))
    await asyncio.gather(*tomove)
    if isinstance(ctx, SlashContext):
      return dict(content=f"Successfully moved {memberCount} member(s)")
    return dict(embed=embed(title=f"Successfully moved {memberCount} member(s)"))

  @commands.command(name="lock",description="Sets your voice channels user limit to the current number of occupants",hidden=True)
  @commands.guild_only()
  # @commands.is_owner()
  @commands.has_guild_permissions(manage_channels=True)
  @commands.bot_has_guild_permissions(manage_channels=True)
  async def norm_lock(self,ctx,*,voicechannel:typing.Optional[discord.VoiceChannel]=None):
    await self.lock(ctx,voicechannel)

  @cog_ext.cog_slash(
    name="lock",
    description="Sets your voice channels user limit to the current number of occupants",
    options=[
      create_option("voicechannel", "The voice channel you wish to lock", 7, required=False)
    ],
    guild_ids=[243159711237537802,805579185879121940]
  )
  @commands.has_guild_permissions(manage_channels=True)
  @commands.bot_has_guild_permissions(manage_channels=True)
  async def slash_lock(self,ctx,*,voicechannel=None):
    await ctx.defer(True)
    post = await self.lock(ctx,voicechannel)
    await ctx.send(hidden=True,**post)

  async def lock(self,ctx,voicechannel:typing.Optional[discord.VoiceChannel]=None):
    # await ctx.guild.chunk(cache=False)
    if voicechannel is None:
      if ctx.author.voice is None:
        if isinstance(ctx, SlashContext):
          return dict(content="You either need to specify a voicechannel or be connected to one")
        return dict(embed=embed(title="You either need to specify a voicechannel or be connected to one",color=MessageColors.ERROR))
      voicechannel = ctx.author.voice.channel
    if voicechannel.user_limit > 0:
      await voicechannel.edit(user_limit=0)
      if isinstance(ctx, SlashContext):
        return dict(content=f"Unlocked `{voicechannel}`")
      return dict(embed=embed(title=f"Unlocked `{voicechannel}`"))
    else:
      await voicechannel.edit(user_limit=len(voicechannel.members))
      if isinstance(ctx, SlashContext):
        return dict(content=f"Locked `{voicechannel}`")
      return dict(embed=embed(title=f"Locked `{voicechannel}`"))

def setup(bot):
  bot.add_cog(ServerManage(bot))
