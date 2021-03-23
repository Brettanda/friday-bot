import discord
from discord.ext import commands
# from discord_slash import cog_ext,SlashContext

from functions import embed

class Ping(commands.Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot


  # @commands.Cog.listener()
  # async def on_ready(self):
  #   self.bot.slash.add_slash_command(self.ping,name="ping",description="Ping",connector=None,guild_ids=[243159711237537802])

  # @cog_ext.cog_slash(name="ping",description="Ping!",guild_ids=[243159711237537802,805579185879121940])
  # async def slash_ping(self,ctx:SlashContext):
  #   await ctx.respond()
  #   # await ctx.delete()
  #   await ctx.send(embed=embed(title="test"))
  #   # await self.ping.__call__(ctx)
  #   # print("something")
  #   # await ctx.invoke(self.bot.get_command('ping'))

  @commands.command(name="ping")
  async def ping(self,ctx):
    # await ctx.respond()
    print("pong")
    try:
      await ctx.send(embed=embed(title="Pong!"))
    except discord.Forbidden:
      await ctx.send("Pong!")

def setup(bot):
  bot.add_cog(Ping(bot))