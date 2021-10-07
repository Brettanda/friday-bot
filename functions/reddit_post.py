# import json
import random
import asyncio
from . import MessageColors, embed

from typing import Union
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from functions import MyContext

posted = {}

lock = asyncio.Lock()


async def get_reddit_post(ctx: Union["MyContext", SlashContext], sub_reddits: Union[str, list] = None, reddit=None):  # ,hidden:bool=False):
  if reddit is None:
    raise TypeError("reddit must not be None")
  if sub_reddits is None:
    raise TypeError("sub_reddits must not be None")

  sub = random.choice(sub_reddits)
  # url = "https://www.reddit.com/r/{}.json?sort=top&t=week".format(sub)

  body = None

  # async with ctx.channel.typing():
  # try:
  body = [i async for i in (await reddit.subreddit(sub)).top("week", params={"count": random.randrange(1000)}, limit=100)]
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
        if len(posted[thisposted]) > 0 and post.permalink in posted[thisposted]:
          del allowed[x]
      except KeyError:
        posted[thisposted] = []
        if len(posted[thisposted]) > 0 and post.permalink in posted[thisposted]:
          del allowed[x]
    x += 1

  def pickPost():
    randNum = random.randint(1, len(allowed)) - 1
    postinquestion = allowed[randNum]

    try:
      if postinquestion.permalink in posted[thisposted]:
        pickPost()
    except KeyError:
      pass

    return postinquestion

  topost = pickPost()
  try:
    posted[thisposted].append(topost.permalink)
  except KeyError:
    posted[thisposted] = [topost.permalink]

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
