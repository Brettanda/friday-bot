import os
import asyncpraw

from nextcord.ext import commands
# from interactions import Context as SlashContext, cog_ext

from functions import MessageColors, embed, MyContext
from typing import Union
import random
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class Meme(commands.Cog):
  """Get a meme hand delivered to you with Friday's meme command"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.subs = ("dankmemes", "memes", "wholesomememes")
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

  async def get_reddit_post(self, ctx: "MyContext", sub_reddits: Union[str, dict] = None, reddit=None):  # ,hidden:bool=False):
    if reddit is None:
      raise TypeError("reddit must not be None")
    if sub_reddits is None:
      raise TypeError("sub_reddits must not be None")

    sub = random.choice(sub_reddits)
    # url = "https://www.reddit.com/r/{}.json?sort=top&t=week".format(sub)

    body = None

    # async with ctx.channel.typing():
    # try:
    # body = await (await reddit.subreddit(sub)).top("week", params={"count": random.randrange(500)}, limit=10)
    body = [i async for i in (await reddit.subreddit(sub)).top("week", params={"count": random.randrange(500)}, limit=10)]
    # async for submission in body:
    #   print(submission.title)
    # post, = [submission async for submission in body.top("week")]  # , params={"count": random.randrange(1000), "limit": 1}):
    # posts += post
    #   body = await request(url)
    # except Exception:
    #   if hidden:
    #     return dict(content="Something went wrong, please try again.")
    #   else:
    #   return dict(embed=embed(title="Something went wrong, please try again.", color=MessageColors.ERROR))

    if ctx.channel is not None and str(ctx.channel.type) == "private":
      thisposted = ctx.channel.id
    elif ctx.guild is not None:
      thisposted = ctx.guild.id
    elif ctx.channel is None and hasattr(ctx, "channel_id"):
      thisposted = ctx.channel_id

    if ctx.channel is not None and str(ctx.channel.type) == "private" or ctx.channel is not None and ctx.channel.nsfw:
      allowed = body
    else:
      allowed = []
      for post in body:
        if not post.over_18 and post.link_flair_text != "MODPOST" and post.link_flair_text != "Long":
          allowed.append(post)

    x = 0
    for post in allowed:
      if "https://i.redd.it/" not in post.url:
        del allowed[x]
      else:
        try:
          if len(self.posted[thisposted]) > 0 and post.permalink in self.posted[thisposted]:
            del allowed[x]
        except KeyError:
          self.posted[thisposted] = []
          if len(self.posted[thisposted]) > 0 and post.permalink in self.posted[thisposted]:
            del allowed[x]
      x += 1

    def pickPost():
      randNum = random.randint(1, len(allowed)) - 1
      postinquestion = allowed[randNum]

      try:
        if postinquestion.permalink in self.posted[thisposted]:
          pickPost()
      except KeyError:
        pass

      return postinquestion

    topost = pickPost()
    try:
      self.posted[thisposted].append(topost.permalink)
    except KeyError:
      self.posted[thisposted] = [topost.permalink]

    data = topost
    # print(data["url"])
    # if hidden:
    #   return dict(
    #     content=f"{data['url']}"
    #     # content=f"{data.get('title')}\n<https://reddit.com{data['permalink']}>\n{data['url']}"
    #   )
    # else:
    return dict(
        embed=embed(
            title=data.title,
            url="https://reddit.com" + data.permalink,
            # author_name="u/"+data.get("author"),
            image=data.url,
            color=MessageColors.MEME
        )
    )

  # @commands.max_concurrency(1,commands.BucketType.channel,wait=False)
  @commands.command(name="meme", aliases=["shitpost"], help="Meme time")
  @commands.cooldown(1, 1, commands.BucketType.user)
  async def norm_meme(self, ctx: "MyContext"):
    async with ctx.typing():
      return await ctx.reply(**await self.get_reddit_post(ctx, self.subs, self.reddit))

  # @cog_ext.cog_slash(name="meme", description="Get a meme hand delivered to you")
  # @checks.slash(user=True, private=True)
  # async def slash_meme(self, ctx: SlashContext):
  #   await ctx.send(**await get_reddit_post(ctx, self.subs, self.reddit))


def setup(bot):
  bot.add_cog(Meme(bot))
