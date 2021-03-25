import re,urllib,json,youtube_dl,ffmpeg,asyncio

import discord
from discord.ext import commands

import os,sys
from functions import embed,MessageColors,ignore_guilds

ytdl_format_options = {
  # 'format': 'bestvideo+bestaudio/worstvideo+worstaudio',
  'format': 'worstvideo+worstaudio/worstvideo',
  # 'audioformat': 'mp3',
  'merge_output_format': 'mp4',
  'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
  # 'max_filesize': '8M',
  'postprocessors': [{
      'key': 'FFmpegVideoConvertor',
      'preferedformat': 'webm'
  }],
  'restrictfilenames': True,
  'noplaylist': True,
  'nocheckcertificate': True,
  'ignoreerrors': False,
  'logtostderr': False,
  'quiet': True,
  # 'no_warnings': True,
  'default_search': 'auto',
  'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class redditlink(commands.Cog):
  def __init__(self,bot):
    self.bot = bot
    self.emoji = "🔗"
    self.pattern = r"https://www.reddit.com/r/[a-zA-Z0-9-_]+/comments/[a-zA-Z0-9]+/[a-zA-Z0-9_-]+"
    self.patternspoiler = r"||https://www.reddit.com/r/[a-zA-Z0-9-_]+/comments/[a-zA-Z0-9]+/[a-zA-Z0-9_-]+||"

  def request(self,url):
    req = urllib.request.Request(
      url,
      headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
      }
    )

    response = urllib.request.urlopen(req)

    return json.loads(response.read())

  @commands.Cog.listener()
  async def on_message(self,ctx):
    if str(ctx.channel.type) != "private" and ctx.guild.id in ignore_guilds:
      # print("ignored guild")
      # logging.info("ignored guild")
      return
    if ctx.author.bot:
      return
    reg = re.findall(self.pattern,ctx.content)
    # spoiler = re.findall(self.patternspoiler,ctx.content)

    if len(reg) != 1:
      return

    body = None
    try:
      body = self.request(reg[0]+".json")
    except:
      raise
      # pass

    data = None
    video = None
    embeded = None
    image = None
    try:
      data = body[0]["data"]["children"][0]["data"]["crosspost_parent_list"][0]
    except:
      data = body[0]["data"]["children"][0]["data"]
      # try:
      # except:
      #   pass

    try:
      if data["media"] != "null":
        video = data["media"]["reddit_video"]["hls_url"]
      # elif len(data["crosspost_parent_list"]) > 0:
      #   video = data["crosspost_parent_list"][0]["media"]["reddit_video"]["hls_url"]
    except:
      # raise
      pass
    
    try:
      embeded = data["media"]["oembed"]
    except:
      pass
    if "i.redd.it" in data["url"]:
      image = data["url"]

    if data["url"] in ctx.content:
      return

    if data["url"].endswith(".html"):
      return

    if data is None and video is None and embeded is None and image is None:
      return

    try:
      await ctx.add_reaction(self.emoji)
    except discord.Forbidden:
      pass

  @commands.Cog.listener()
  async def on_raw_reaction_add(self,payload):
    guild = self.bot.get_guild(payload.guild_id)
    if guild is None:
      return
    channel = guild.get_channel(payload.channel_id)
    if channel is None:
      return
    message = await channel.fetch_message(payload.message_id)
    if message is None:
      return
    # TODO: check the max file size of the server and change the quality of the video to match
    if self.bot.user == payload.member or self.bot.user == payload.member.bot:
      return
    if payload.member != message.author:
      return
    if payload.emoji.name == self.emoji:
      test:bool = False
      for react in message.reactions:
        if react.me and react.emoji == self.emoji:
          test = True
        if test == False:
          return
      try:
        await asyncio.gather(
          message.remove_reaction(self.emoji,self.bot.user),
          message.remove_reaction(self.emoji,payload.member)
        )
      except:
        pass
      async with message.channel.typing():

        reg = re.findall(self.pattern,message.content)

        if len(reg) != 1:
          return

        body = None
        try:
          body = self.request(reg[0]+".json")
        except:
          pass
          
        try:
          try:
            data = body[0]["data"]["children"][0]["data"]["crosspost_parent_list"][0]
          except:
            data = body[0]["data"]["children"][0]["data"]
        except KeyError:
          await message.reply(embed=embed(title="There was a problem connecting to reddit",color=MessageColors.ERROR))
          return

        link = None
        linkdata = None
        video = False
        # try:
        if data["media"] != None and "reddit_video" in data["media"]:
          link = data["media"]["reddit_video"]["hls_url"]
          loop = asyncio.get_event_loop()
          linkdata = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=True))
          ext = "webm" #linkdata['ext']
          video = True
          # linkdata = await ytdl.extract_info(link, download=True)

          if 'entries' in linkdata:
            # take first item from a playlist
            linkdata = linkdata['entries'][0]
          # link = linkdata["url"]
          # pprint.pprint(linkdata)
          # print(f'{linkdata["extractor"]}-{linkdata["id"]}-{linkdata["title"]}.{linkdata["ext"]}')
          # link = data["media"]["reddit_video"]["fallback_url"]
        else:
          link = data["url"]
        # except:
        #   raise

      # TODO: Does not get url for videos atm
      if (message.channel.nsfw == True and data["over_18"] == True) or (message.channel.nsfw == False and data["over_18"] == False) or (message.channel.nsfw == True and data["over_18"] == False):
        spoiler = False
      else:
        spoiler = True

      if video == True:
        thispath = os.getcwd()
        if "\\" in thispath:
          seperator = "\\\\"
        else:
          seperator = "/"
        mp4file = f'{thispath}{seperator}{linkdata["extractor"]}-{linkdata["id"]}-{linkdata["title"]}.{ext}'
        try:
          # name = f'{linkdata["extractor"]}-{linkdata["id"]}-{linkdata["title"]}.{linkdata["ext"]}'
          name = data["title"].split()
          await message.reply(file=discord.File(fp=mp4file,filename=f'{"_".join(name)}.{ext}',spoiler=spoiler))
        except discord.HTTPException:
          await message.reply(embed=embed(title="This file is too powerful to be uploaded",description="You will have to open reddit to view this",color=MessageColors.ERROR))
          pass
        finally:
          try:
            os.remove(mp4file)
          except PermissionError:
            pass
      else:
        if spoiler == True:
          await message.reply("||"+link+"||")
        else:
          await message.reply(link)
      # elif reaction.message.channel.nsfw == False and data["over_18"] == False:
          
      # print(len(body))
      # if ctx.channel.nsfw and body["data"]["over_18"]:


      # await ctx.reply(embed=embed(title="Meme"))
      # return embed(title="Meme")
      # if self.bot.user == reaction.message.reactions

def setup(bot):
  bot.add_cog(redditlink(bot))