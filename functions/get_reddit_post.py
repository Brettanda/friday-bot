import discord,aiohttp,json,random
from discord.ext import commands
from functions import embed,MessageColors

posted = {}

async def request(url):
  async with aiohttp.ClientSession() as session:
    async with session.get(
      url,
      headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
      }
    ) as r:
      if r.status == 200:
        return await r.json()

async def get_reddit_post(ctx:commands.Context,sub_reddits:str or list=None):
  if sub_reddits is None:
    raise TypeError("sub_reddits must not be None")
  
  url = "https://www.reddit.com/r/{}.json?sort=top&t=week".format(random.choice(sub_reddits))

  body = None

  async with ctx.channel.typing():
    try:
      body = await request(url)
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
      else:
        try:
          if len(posted[thisposted]) > 0 and post["data"].get("permalink") in posted[thisposted]:
            del allowed[x]
        except KeyError:
          posted[thisposted] = []
          if len(posted[thisposted]) > 0 and post["data"].get("permalink") in posted[thisposted]:
            del allowed[x]
        except:
          raise
      x += 1

    def pickPost():
      randNum = random.randint(1,len(allowed)) - 1
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
  return dict(
    embed=embed(
      title=data.get("title"),
      url="https://reddit.com"+data["permalink"],
      # author_name="u/"+data.get("author"),
      image=data["url"],
      color=MessageColors.MEME
    )
  )
  