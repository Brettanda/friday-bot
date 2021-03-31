from discord.ext import commands
from discord_slash import SlashContext, cog_ext

from functions import get_reddit_post

class Meme(commands.Cog):
  def __init__(self,bot):
    self.bot = bot
    self.subs = ["dankmemes", "memes"]
    self.posted = {}

  @commands.command(name="meme",aliases=["shitpost"])
  @commands.max_concurrency(1,commands.BucketType.channel,wait=True)
  async def meme(self,ctx):
    post = await get_reddit_post(ctx,self.subs)
    
    await ctx.reply(**post)

def setup(bot):
  bot.add_cog(Meme(bot))
