import discord
from discord.ext import commands

from functions import embed,MessageColors,mydb_connect,query

class ServerManage(commands.Cog):
  """Commands for managing Friday on your server"""

  def __init__(self,bot):
    self.bot = bot

  # @commands.group(name="server",invoke_without_command=True,hidden=True)
  # @commands.guild_only()
  # @commands.is_owner()
  # @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  # async def server(self,ctx):
  #   await ctx.reply(embed=embed(title="Invalid subcommand",color=MessageColors.ERROR))
  
  @commands.command(name="defaultrole",hidden=True)
  @commands.guild_only()
  @commands.is_owner()
  @commands.has_guild_permissions(manage_roles=True)
  @commands.bot_has_permissions(send_messages = True, read_messages = True)
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
  @commands.guild_only()
  @commands.has_guild_permissions(administrator=True)
  @commands.bot_has_permissions(send_messages = True, read_messages = True)
  async def _prefix(self,ctx,new_prefix:str="!"):
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

  @commands.command(name="musicchannel",description="Set the channel where I can join and play music. If none then I will join any VC",hidden=True)
  @commands.guild_only()
  @commands.is_owner()
  @commands.has_guild_permissions(administrator=True)
  @commands.bot_has_permissions(send_messages = True, read_messages = True)
  async def music_channel(self,ctx,voicechannel:discord.VoiceChannel=None):
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
  @commands.guild_only()
  @commands.has_guild_permissions(administrator=True)
  @commands.bot_has_permissions(send_messages = True, read_messages = True)
  async def delete_commands_after(self,ctx,time:int=0):
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
  @commands.guild_only()
  @commands.bot_has_guild_permissions(kick_members=True)
  @commands.has_guild_permissions(kick_members=True)
  @commands.bot_has_permissions(send_messages = True, read_messages = True)
  async def kick(self,ctx,member:discord.Member,*,reason:str):
    if member == self.bot.user:
      try:
        await ctx.add_reaction("😢")
      except:
        pass
      return
    if member == ctx.author:
      await ctx.reply(embed=embed(title="Failed to kick yourself",color=MessageColors.ERROR))
      return
    try:
      await member.kick(reason=f"{ctx.author}: {reason}")
    except discord.Forbidden:
      raise commands.BotMissingPermissions(["kick_members"])
    await ctx.reply(embed=embed(title=f"Kicked `{member}` for reason `{reason}`"))
  
  @commands.command(name="ban")
  @commands.guild_only()
  @commands.bot_has_guild_permissions(ban_members=True)
  @commands.has_guild_permissions(ban_members=True)
  @commands.bot_has_permissions(send_messages = True, read_messages = True)
  async def ban(self,ctx,member:discord.Member,*,reason:str):
    if member == self.bot.user:
      try:
        await ctx.add_reaction("😢")
      except:
        pass
      return
    if member == ctx.author:
      await ctx.reply(embed=embed(title="Failed to ban yourself",color=MessageColors.ERROR))
      return
    try:
      await member.ban(reason=f"{ctx.author}: {reason}")
    except discord.Forbidden:
      raise commands.BotMissingPermissions(["ban_members"])
    await ctx.reply(embed=embed(title=f"Banned `{member}` for reason `{reason}`"))


def setup(bot):
  bot.add_cog(ServerManage(bot))