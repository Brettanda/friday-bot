# import json
import random
import asyncio

import aiohttp
# import discord
from discord.ext import commands

from discord_slash import SlashContext

from functions import MessageColors, embed

posted = {}

lock = asyncio.Lock()


async def request(url):
  async with aiohttp.ClientSession() as session:
    async with session.get(
        url,
        headers={
            'User-Agent':
            'DiscordBot (https://github.com/Rapptz/discord.py 1.7.2) Python/3.8 aiohttp/3.7.4'
        }
    ) as r:
      if r.status == 200:
        return await r.json()


async def get_reddit_post(ctx: commands.Context or SlashContext, sub_reddits: str or list = None):  # ,hidden:bool=False):
  if sub_reddits is None:
    raise TypeError("sub_reddits must not be None")

  url = "https://www.reddit.com/r/{}.json?sort=top&t=week".format(random.choice(sub_reddits))

  body = None

  # async with ctx.channel.typing():
  try:
    async with lock:
      body = await request(url)
  except BaseException:
    # if hidden:
      # return dict(content="Something went wrong, please try again.")
    # else:
    return dict(embed=embed(title="Something went wrong, please try again.", color=MessageColors.ERROR))

  if str(ctx.channel.type) == "private":
    thisposted = ctx.channel.id
  else:
    thisposted = ctx.guild.id

  if str(ctx.channel.type) == "private" or ctx.channel.nsfw:
    allowed = body["data"]["children"]
  else:
    allowed = []
    for post in body["data"]["children"]:
      if not post["data"]["over_18"] and post["data"]["link_flair_text"] != "MODPOST" and post["data"]["link_flair_text"] != "Long":
        allowed.append(post)

  x = 0
  for post in allowed:
    if "https://i.redd.it/" not in post["data"]["url"]:
      del allowed[x]
    else:
      try:
        if len(posted[thisposted]) > 0 and post["data"].get("permalink") in posted[thisposted]:
          del allowed[x]
      except KeyError:
        posted[thisposted] = []
        if len(posted[thisposted]) > 0 and post["data"].get("permalink") in posted[thisposted]:
          del allowed[x]
    x += 1

  def pickPost():
    randNum = random.randint(1, len(allowed)) - 1
    postinquestion = allowed[randNum]

    try:
      if postinquestion["data"].get("permalink") in posted[thisposted]:
        pickPost()
    except KeyError:
      pass

    return postinquestion

  topost = pickPost()
  try:
    posted[thisposted].append(topost["data"].get("permalink"))
  except KeyError:
    posted[thisposted] = [topost["data"].get("permalink")]

  data = topost["data"]
  # print(data["url"])
  # if hidden:
  #   return dict(
  #     content=f"{data['url']}"
  #     # content=f"{data.get('title')}\n<https://reddit.com{data['permalink']}>\n{data['url']}"
  #   )
  # else:
  return dict(
      embed=embed(
          title=data.get("title"),
          url="https://reddit.com" + data["permalink"],
          # author_name="u/"+data.get("author"),
          image=data["url"],
          color=MessageColors.MEME
      )
  )
