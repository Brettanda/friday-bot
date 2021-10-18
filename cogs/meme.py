import os
import asyncpraw

from discord.ext import commands
from discord_slash import SlashContext, cog_ext

from functions import get_reddit_post, checks, MyContext
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class Meme(commands.Cog):
  """Get a meme hand delivered to you with Friday's meme command"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.subs = ["dankmemes", "memes", "wholesomememes"]
    self.posted = {}
    self.reddit = asyncpraw.Reddit(
        client_id=os.environ.get('REDDITCLIENTID'),
        client_secret=os.environ.get('REDDITCLIENTSECRET'),
        password=os.environ.get('REDDITPASSWORD'),
        user_agent="Friday Discord bot v1.0.0  (by /u/Motostar19)",
        username="Friday"
    )
    self.reddit.read_only = True

  def __repr__(self):
    return "<cogs.Meme>"

  # @commands.max_concurrency(1,commands.BucketType.channel,wait=False)
  @commands.command(name="meme", aliases=["shitpost"], help="Meme time")
  @commands.cooldown(1, 1, commands.BucketType.user)
  async def norm_meme(self, ctx: "MyContext"):
    if not ctx.is_interaction():
      async with ctx.typing():
        return await ctx.reply(**await get_reddit_post(ctx, self.subs, self.reddit))
    await ctx.reply(**await get_reddit_post(ctx, self.subs, self.reddit))

  @cog_ext.cog_slash(name="meme", description="Meme time")
  @checks.slash(user=True, private=True)
  async def slash_meme(self, ctx: SlashContext):
    await ctx.send(**await get_reddit_post(ctx, self.subs, self.reddit))


def setup(bot):
  bot.add_cog(Meme(bot))
