import discord
from discord.ext import commands
from discord_slash import cog_ext,SlashContext

from functions import embed

class Ping(commands.Cog):
  def __init__(self,bot):
    self.bot = bot

  @commands.command(name="ping",description="Pong!")
  async def norm_ping(self,ctx):
    post = await self.ping(ctx)
    await ctx.reply(**post)

  @cog_ext.cog_slash(name="ping",description="Ping!")
  async def slash_ping(self,ctx:SlashContext):
    await ctx.respond(True)
    post = await self.ping(ctx)
    await ctx.send_hidden(**post)

  async def ping(self,ctx):
    if isinstance(ctx, SlashContext):
      return dict(content="Pong!")
    else:
      return dict(embed=embed(title="Pong!"))

def setup(bot):
  bot.add_cog(Ping(bot))