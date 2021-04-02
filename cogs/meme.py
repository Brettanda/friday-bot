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

  @cog_ext.cog_slash(
      name="meme",
      description="Meme time",
      # options=[
      #   create_option(
      #     "hidden",
      #     "To hide the meme, or not to hide the meme",
      #     5,
      #     required=False
      #   )
      # ],
      guild_ids=[243159711237537802, 805579185879121940])
  # @commands.cooldown(1,1, commands.BucketType.channel)
  # @commands.max_concurrency(1,commands.BucketType.channel,wait=False)
  async def slash_meme(self, ctx: SlashContext):  # ,hidden:bool=False):
    await ctx.defer()  # hidden)
    post = await get_reddit_post(ctx, self.subs)
    # if hidden:
    #   await ctx.send(hidden=True,**post)
    # else:
    await ctx.send(**post)


def setup(bot):
  bot.add_cog(Meme(bot))
