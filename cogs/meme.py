from discord.ext import commands
from discord_slash import SlashContext, cog_ext

from functions import get_reddit_post


class Meme(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.subs = ["dankmemes", "memes", "wholesomememes"]
    self.posted = {}

  @commands.command(name="meme", aliases=["shitpost"], description="Meme time")
  @commands.cooldown(1, 1, commands.BucketType.user)
  # @commands.max_concurrency(1,commands.BucketType.channel,wait=False)
  async def norm_meme(self, ctx):
    async with ctx.typing():
      post = await get_reddit_post(ctx, self.subs)
    await ctx.reply(**post)

  @cog_ext.cog_slash(name="meme", description="Meme time")
  async def slash_meme(self, ctx: SlashContext):
    await ctx.send(**await get_reddit_post(ctx, self.subs))


def setup(bot):
  bot.add_cog(Meme(bot))
