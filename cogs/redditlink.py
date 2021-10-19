import youtube_dl
import discord
import asyncio
# import urllib
# import aiohttp
# import sys
import re
import os
# import json
import asyncpraw

# import ffmpeg
from discord.ext import commands
from discord_slash import cog_ext

from functions import MessageColors, embed
from typing_extensions import TYPE_CHECKING
from functions import MyContext

if TYPE_CHECKING:
  from index import Friday as Bot


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
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class redditlink(commands.Cog):
  """Extract the media from Reddit posts with Friday's Reddit command and more"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.emoji = "🔗"
    self.lock = asyncio.Lock()
    self.pattern = r"https:\/\/(?:www\.|)reddit.com\/r\/[a-zA-Z0-9-_]+\/comments\/[a-zA-Z0-9]+\/[a-zA-Z0-9_-]+"
    self.patternspoiler = r"||https:\/\/(?:www\.|)reddit.com\/r\/[a-zA-Z0-9-_]+\/comments\/[a-zA-Z0-9]+\/[a-zA-Z0-9_-]+||"
    self.reddit = asyncpraw.Reddit(
        client_id=os.environ.get('REDDITCLIENTID'),
        client_secret=os.environ.get('REDDITCLIENTSECRET'),
        password=os.environ.get('REDDITPASSWORD'),
        user_agent="Friday Discord bot v1.0.0  (by /u/Motostar19)",
        username="Friday"
    )
    self.reddit.read_only = True

  @commands.Cog.listener()
  async def on_message(self, message: discord.Message):
    if message.author.bot:
      return
    # required_perms = [("add_reactions",True)]
    # guild = ctx.guild
    # me = guild.me if guild is not None else self.bot.user
    # permissions = ctx.channel.permissions_for(me)
    # missing = [perm for perm,value in required_perms if getattr(permissions,perm) != value]

    # if missing:
    #   return

    # TODO: remove this check when members intent
    if not message.guild:
      return

    reg = re.findall(self.pattern, message.content)
    # spoiler = re.findall(self.patternspoiler,ctx.content)

    if len(reg) != 1:
      return

    if message.guild:
      db_enabled = await self.bot.db.query("SELECT reddit_extract FROM servers WHERE id=$1 LIMIT 1", str(message.guild.id))
      if not db_enabled:
        return

    ctx: "MyContext" = await self.bot.get_context(message)
    if ctx.command is not None:
      return
    body = await self.reddit.submission(url=reg[0])

    data, video, embeded, image = body, None, None, None

    try:
      if data.media is not None:
        video = data.media["reddit_video"]["hls_url"]
      # elif len(data["crosspost_parent_list"]) > 0:
      #   video = data["crosspost_parent_list"][0]["media"]["reddit_video"]["hls_url"]
    except Exception:
      pass

    try:
      embeded = data.media["oembed"]
    except Exception:
      pass
    if "i.redd.it" in data.url:
      image = data.url

    if data.url in message.content:
      return

    if data.url.endswith(".html"):
      return

    if data is None and video is None and embeded is None and image is None:
      return

    try:
      await message.add_reaction(self.emoji)
    except (discord.Forbidden, discord.NotFound):
      pass

  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
    if payload.emoji.name != self.emoji or payload.member.bot or not payload.guild_id:
      return
    channel = self.bot.get_channel(payload.channel_id)
    if not channel:
      return
    message = await channel.fetch_message(payload.message_id)
    if not message:
      return
    if payload.user_id != message.author.id:
      return
    if len([react.emoji for react in message.reactions if react.me and react.emoji == self.emoji]) < 1:
      return
    try:
      await message.clear_reaction(self.emoji)
    except BaseException:
      pass
    guild = self.bot.get_guild(payload.guild_id)
    async with channel.typing():
      try:
        await self.extract(message.content, payload=payload, guild=guild, channel=channel, message=message)
      except Exception as e:
        await message.reply(embed=embed(title="Something went wrong", description="Please try again later. I have notified my boss of this error", color=MessageColors.ERROR), mention_author=False)
        raise e

  @commands.group(name="redditextract", help="Extracts the media from the reddit post", invoke_without_command=True)
  async def norm_extract(self, ctx: "MyContext", link: str):
    if not ctx.is_interaction():
      try:
        async with ctx.typing():
          return await self.extract(query=link, command=True, ctx=ctx, guild=ctx.guild, channel=ctx.channel)
      except Exception:
        return await self.extract(query=link, command=True, ctx=ctx, guild=ctx.guild, channel=ctx.channel)

    return await self.extract(query=link, command=True, ctx=ctx, guild=ctx.guild, channel=ctx.channel)

  @norm_extract.command("enable", help="Enable or disabled Friday's reddit link extraction. (When disabled Friday won't react to reddit links.)")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True)
  async def extract_toggle(self, ctx, enable: bool):
    await self.bot.db.query("UPDATE servers SET reddit_extract=$1 WHERE id=$2", enable, str(ctx.guild.id))
    if enable:
      return await ctx.send(embed=embed(title="I will now react to Reddit links", description="For me to then extract a reddit link the author of the message must react with the same emoji Friday did.\nFriday also requires add_reaction permissions (if not already) for this to work."))
    await ctx.send(embed=embed(title="I will no longer react to Reddit links.", description="The Reddit extract commands will still work."))

  @cog_ext.cog_slash(name="redditextract", description="Extracts the file from the reddit post")
  async def slash_extract(self, ctx, link: str):
    await ctx.defer()
    await self.extract(query=link, command=True, ctx=ctx, guild=ctx.guild, channel=ctx.channel)

  async def extract(self, query, command: bool = False, payload: discord.RawReactionActionEvent = None, ctx: "MyContext" = None, guild=None, channel: discord.TextChannel = None, message: discord.Message = None):
    if ctx is None and message is not None:
      ctx = await self.bot.get_context(message)
    if guild is None and not ctx.guild_id:
      raise commands.ArgumentParsingError()
    if channel is None and not ctx.channel_id:
      raise commands.ArgumentParsingError()
    if message is None and not command:
      raise commands.ArgumentParsingError()
    # TODO: check the max file size of the server and change the quality of the video to match
    reg = re.findall(self.pattern, query)

    if len(reg) != 1:
      return await ctx.send(embed=embed(title="That is not a reddit post url", color=MessageColors.ERROR))

    data = await self.reddit.submission(url=reg[0])

    link, linkdata, video = None, None, None
    # try:
    if data.media is not None and "reddit_video" in data.media:
      link = data.media["reddit_video"]["hls_url"]
      content_length = 0
      async with self.lock:
        async with self.bot.session.get(
                link,
                headers={
                    'User-Agent':
                    'Friday Discord bot v1.0.0  (by /u/Motostar19)'
                }) as r:
          if r.status == 200:
            content_length = r.content_length
      loop = asyncio.get_event_loop()
      linkdata = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, content_length))
      ext = "webm"  # linkdata['ext']
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
      link = data.url
    # except:
    #   raise

    # TODO: Does not get url for videos atm
    channel = message.channel if payload is not None else ctx.channel
    nsfw = channel.nsfw if channel is not None and not isinstance(channel, discord.Thread) else channel.parent.nsfw if channel is not None and isinstance(channel, discord.Thread) else False
    if (nsfw is True and data.over_18 is True) or (nsfw is False and data.over_18 is False) or (nsfw is True and data.over_18 is False):
      spoiler = False
    else:
      spoiler = True

    if video is True:
      thispath = os.getcwd()
      if "\\" in thispath:
        seperator = "\\\\"
      else:
        seperator = "/"
      mp4file = f'{thispath}{seperator}{linkdata["extractor"]}-{linkdata["id"]}-{linkdata["title"]}.{ext}'
      try:
        # name = f'{linkdata["extractor"]}-{linkdata["id"]}-{linkdata["title"]}.{linkdata["ext"]}'
        name = data.title.split()
        return await ctx.send(file=discord.File(fp=mp4file, filename=f'friday-bot.com_{"_".join(name)}.{ext}', spoiler=spoiler))
      except discord.HTTPException:
        return await ctx.send(embed=embed(title="This file is too powerful to be uploaded", description="You will have to open reddit to view this", color=MessageColors.ERROR))
      finally:
        try:
          os.remove(mp4file)
        except PermissionError:
          pass
    else:
      if spoiler is True:
        return await ctx.send(content="||" + link + "||")
      else:
        return await ctx.send(content=link)
    # elif reaction.message.channel.nsfw == False and data["over_18"] == False:

    # print(len(body))
    # if ctx.channel.nsfw and body["data"]["over_18"]:

    # await ctx.reply(embed=embed(title="Meme"))
    # return embed(title="Meme")
    # if self.bot.user == reaction.message.reactions


def setup(bot):
  bot.add_cog(redditlink(bot))
