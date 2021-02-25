import discord
from discord.ext import commands

from functions import embed,MessageColors

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
  
  @server.command(name="defaultrole")
  @commands.guild_only()
  @commands.is_owner()
  @commands.has_guild_permissions(manage_roles=True)
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def defaultrole(self,ctx,role:discord.Role):
    await ctx.reply(embed=embed(title=f"The new default role for new members is `{role}`"))

  # @server.command(name="prefix",hidden=True)
  # @commands.is_owner()
  # @commands.guild_only()
  # @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  # async def prefix(self,ctx,new_prefix:str):
  #   if len(new_prefix) > 3:
  #     print(f"max string met: {len(new_prefix)}")
  #   appinfo = await self.bot.application_info()
  #   if ctx.message.author.id != appinfo.owner.id:
  #     return
  #   # if ctx.message.author.guild_permissions.administrator != True:
  #   #   return
  #   await ctx.reply(embed=embed(title=f"My new prefix is `{new_prefix}`"))

def setup(bot):
  bot.add_cog(ServerSettings(bot))