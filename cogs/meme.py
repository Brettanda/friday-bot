from __future__ import annotations

import asyncio
import os
import random
from typing import TYPE_CHECKING, Union

import asyncpraw
import discord
from discord.ext import commands
from expiringdict import ExpiringDict

from functions import MessageColors, MyContext, embed

if TYPE_CHECKING:
  from index import Friday


class Meme(commands.Cog):
  """Get a meme hand delivered to you with Friday's meme command"""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot
    self.subs = ("dankmemes", "memes", "wholesomememes")
    self.posted = ExpiringDict(max_len=1000, max_age_seconds=18000.0)
    self.reddit_lock = asyncio.Lock(loop=bot.loop)
    self.reddit = asyncpraw.Reddit(
        client_id=os.environ.get('REDDITCLIENTID'),
        client_secret=os.environ.get('REDDITCLIENTSECRET'),
        password=os.environ.get('REDDITPASSWORD'),
        user_agent="Friday Discord bot v1.0.0  (by /u/Motostar19)",
        username="Friday"
    )
    self.reddit.read_only = True

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def get_reddit_post(self, ctx: MyContext, sub_reddits: Union[str, tuple], reddit=None) -> dict:  # ,hidden:bool=False):
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
    async with self.reddit_lock:
      body = [i async for i in (await reddit.subreddit(sub)).top("week", params={"count": 500}, limit=10)]
    # async for submission in body:
    #   print(submission.title)
    # post, = [submission async for submission in body.top("week")]  # , params={"count": random.randrange(1000), "limit": 1}):
    # posts += post
    #   body = await request(url)
    # except Exception:
    #   if hidden:
    #     return dict(content="Something went wrong, please try again.")
    #   else:
    #   return dict(embed=embed(title="Something went wrong, please try again.", color=MessageColors.error()))

    thisposted = ctx.channel and ctx.channel.id
    # thisposted = hasattr(ctx, "channel_id") and ctx.channel_id or thisposted
    thisposted = ctx.guild and ctx.guild.id or thisposted

    if ctx.channel and ctx.channel.type == discord.ChannelType.private or ctx.channel and getattr(ctx.channel, "nsfw", None):
      allowed = body
    else:
      allowed = [post for post in body if not post.over_18 and post.link_flair_text != "MODPOST" and post.link_flair_text != "Long"]

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
      post, x = allowed[random.randint(1, len(allowed)) - 1], 0
      while post.permalink in self.posted[thisposted] and x < 1000:
        post = allowed[random.randint(1, len(allowed)) - 1]
        x += 1

      return post

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
            color=MessageColors.meme()
        )
    )

  @commands.command(name="meme", aliases=["shitpost"], help="Meme time")
  @commands.max_concurrency(1, commands.BucketType.guild, wait=True)
  # @commands.cooldown(1, 1, commands.BucketType.user)
  async def norm_meme(self, ctx: MyContext):
    try:
      async with ctx.typing():
        await ctx.reply(**await self.get_reddit_post(ctx, self.subs, self.reddit))
    except discord.Forbidden:
      pass


async def setup(bot):
  await bot.add_cog(Meme(bot))
