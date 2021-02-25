import discord
from discord.ext import commands

from functions import embed,MessageColors,mydb_connect,query

class ServerSettings(commands.Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot

  @commands.group(name="server",invoke_without_command=True,hidden=True)
  @commands.guild_only()
  @commands.is_owner()
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def server(self,ctx):
    await ctx.reply(embed=embed(title="Invalid subcommand",color=MessageColors.ERROR))
  
  @server.command(name="defaultrole",hidden=True)
  @commands.guild_only()
  @commands.is_owner()
  @commands.has_guild_permissions(manage_roles=True)
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def _defaultrole(self,ctx,role:discord.Role):
    # TODO: Need the members intent so assign the role
    try:
      mydb = mydb_connect()
      query(mydb,f"UPDATE servers SET defaultRole=%s WHERE id=%s",role.id,ctx.guild.id)
    except:
      raise
    else:
      await ctx.reply(embed=embed(title=f"The new default role for new members is `{role}`"))

  @server.command(name="prefix",hidden=True)
  @commands.guild_only()
  @commands.is_owner()
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
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
      await ctx.reply(embed=embed(title=f"My new prefix is `{new_prefix}`"))



def setup(bot):
  bot.add_cog(ServerSettings(bot))