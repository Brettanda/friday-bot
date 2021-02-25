from discord import Embed
from discord.ext.commands import Cog
from discord.ext import commands

import os,sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from functions import *

import aiohttp
import json,random

class Meme(Cog):
  def __init__(self,bot):
    self.bot = bot
    self.subs = ["dankmemes", "memes"]
    self.posted = {}

  async def req(self,url):
    async with aiohttp.ClientSession() as session:
      async with session.get(
        url,
        headers={
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
        }
      ) as r:
        if r.status == 200:
          return await r.json()

  @commands.command(name="meme")
  @commands.cooldown(1,7, commands.BucketType.user)
  @commands.bot_has_permissions(send_messages = True, embed_links = True, read_messages = True)
  async def meme(self,ctx):
    num = random.randint(1,len(self.subs))
    num = num - 1
    url = "https://www.reddit.com/r/{}.json?sort=top&t=week".format(self.subs[num])

    body = None

    async with ctx.typing():
      try:
        body = await self.req(url)
      except:
        await ctx.reply(embed=embed(title="Something went wrong, please try again.",color=MessageColors.ERROR))
        return

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
        try:
          if len(self.posted[thisposted]) > 0 and post["data"].get("permalink") in self.posted[thisposted]:
            del allowed[x]
        except:
          pass
        x += 1

      def pickPost():
        randNum = random.randint(1,len(allowed)) - 1
        postinquestion = allowed[randNum]

        try:
          if postinquestion["data"].get("permalink") in self.posted[thisposted]:
            pickPost()
        except KeyError:
          pass

        return postinquestion

      topost = pickPost()
      try:
        self.posted[thisposted].append(topost["data"].get("permalink"))
      except KeyError:
        self.posted[thisposted] = [topost["data"].get("permalink")]

    data = topost["data"]
    await ctx.reply(
      embed=embed(
        title=data.get("title"),
        url="https://reddit.com"+data["permalink"],
        # author_name="u/"+data.get("author"),
        image=data["url"],
        color=MessageColors.MEME
      )
    )

  # @meme.error
  # async def on_cooldown(self,error,ctx):
  #   if isinstance(error,commands.CommandOnCooldown):
      
  #   else:
  #     raise error

def setup(bot):
  bot.add_cog(Meme(bot))