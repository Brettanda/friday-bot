from discord.ext import commands
from discord_slash import SlashContext, cog_ext

from functions import get_reddit_post, checks, MyContext
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class Meme(commands.Cog):
  """Memes"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.subs = ["dankmemes", "memes", "wholesomememes"]
    self.posted = {}

  # @commands.max_concurrency(1,commands.BucketType.channel,wait=False)
  @commands.command(name="meme", aliases=["shitpost"], help="Meme time")
  @commands.cooldown(1, 1, commands.BucketType.user)
  async def norm_meme(self, ctx: "MyContext"):
    if not ctx.is_interaction():
      async with ctx.typing():
        return await ctx.reply(**await get_reddit_post(ctx, self.subs))
    await ctx.reply(**await get_reddit_post(ctx, self.subs))

  @cog_ext.cog_slash(name="meme", description="Meme time")
  @checks.slash(user=True, private=True)
  async def slash_meme(self, ctx: SlashContext):
    await ctx.send(**await get_reddit_post(ctx, self.subs))


def setup(bot):
  bot.add_cog(Meme(bot))
