from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import TYPE_CHECKING, Optional

# import ffmpeg
import asyncpg
import asyncpraw
import discord
import yarl
import youtube_dl
from discord.ext import commands

from functions import MessageColors, MyContext, cache, embed, exceptions

if TYPE_CHECKING:
  from typing_extensions import Self

  from functions.custom_contexts import GuildContext
  from index import Friday

log = logging.getLogger(__name__)


class ExtractionError(commands.CommandError):
  pass


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


PATTERN = r"<?https?:\/\/(?:www\.)?reddit\.com\/r\/[a-zA-Z\d_-]+\/comments\/[a-zA-Z%\d_-]+\/[a-zA-Z%\d_-]+>?"
PATTERN_SPOILER = r"||<?https?:\/\/(?:www\.)?reddit\.com\/r\/[a-zA-Z\d_-]+\/comments\/[a-zA-Z%\d_-]+\/[a-zA-Z%\d_-]+>?||"

REDDIT_CLIENT_ID = os.environ.get("REDDITCLIENTID")
REDDIT_CLIENT_SECRET = os.environ.get("REDDITCLIENTSECRET")
REDDIT_PASSWORD = os.environ.get("REDDITPASSWORD")


class MustBeAuthor(exceptions.Base):
  def __init__(self, message="You must be the author of the message to extract the media"):
    super().__init__(message=message)


class NotRedditLink(exceptions.Base):
  def __init__(self, message="The message must contain a proper Reddit post with media to extract"):
    super().__init__(message=message)


class Config:
  __slots__ = ("bot", "id", "enabled", )

  def __init__(self, *, record: asyncpg.Record, bot: Friday):
    self.bot: Friday = bot
    self.id: int = int(record["id"], base=10)
    self.enabled: bool = bool(record["reddit_extract"])


class RedditMedia:
  def __init__(self, url: yarl.URL, submission: asyncpraw.models.Submission):
    self.url: yarl.URL = url
    self.submission: asyncpraw.models.Submission = submission
    self.needs_extraction: bool = False

  @classmethod
  async def no_context(cls, bot: Friday, argument: str) -> Self:
    try:
      url = yarl.URL(argument)
    except Exception:
      raise commands.BadArgument("The argument must be a valid Reddit URL")
    headers = {
            'User-Agent': 'Discord:Friday:v1.0 (by /u/Motostar19)',
    }

    if url.host == 'v.redd.it':
      # have to do a request to fetch the 'main' URL.
      async with bot.session.get(url, headers=headers) as resp:
        url = resp.url

    is_valid_path = url.host and url.host.endswith('reddit.com')
    if not is_valid_path:
      raise commands.BadArgument('Not a reddit URL.')

    redditlink_cog: redditlink = bot.get_cog("redditlink")  # type: ignore
    submission = await redditlink_cog.reddit.submission(url=str(url))
    media = None
    needs_extraction = False
    try:
      if submission.media is not None:
        media = submission.media["reddit_video"]["hls_url"]
        needs_extraction = True
    except Exception:
      pass

    try:
      media = submission.media["oembed"]
    except Exception:
      pass
    if "i.redd.it" in submission.url:
      media = submission.url

    if str(url) in submission.url:
      raise commands.BadArgument("Nothing to extract from this URL")

    'https://www.reddit.com/r/GPT3/comments/q2gr84/how_to_get_multiple_outputs_from_the_same_prompt/'
    'https://www.reddit.com/r/GPT3/comments/q2gr84/how_to_get_multiple_outputs_from_the_same_prompt'
    if submission.url.endswith(".html"):
      raise commands.BadArgument("Can't extract from this URL")

    if media is None:
      raise commands.BadArgument('Could not fetch media information.')
    self = cls(media, submission)
    self.needs_extraction = needs_extraction
    return self

  @classmethod
  async def convert(cls, ctx: MyContext, argument: str) -> Self:
    async with ctx.typing():
      cog: redditlink = ctx.bot.get_cog("redditlink")  # type: ignore
      return await cog.get_reddit_post(argument)


class redditlink(commands.Cog):
  """Extract the media from Reddit posts with Friday's Reddit command and more.

    Friday has a feature that will extract Reddit media. To use this feature
    simply paste the link to a Reddit post in a text channel and Friday will
    react with 🔗 if media is extractable. To extract the media just react
    with 🔗 as well, and Friday will begin the process.
  """

  def __init__(self, bot: Friday):
    self.bot: Friday = bot

    self.emoji = "🔗"

    self.session_lock = asyncio.Lock(loop=bot.loop)
    self.extract_lock = asyncio.Lock(loop=bot.loop)
    self.reddit = asyncpraw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        password=REDDIT_PASSWORD,
        user_agent="Discord:Friday:v1.0 (by /u/Motostar19)",
        username="Motostar19"
    )
    self.reddit.read_only = True

  @cache.cache()
  async def get_guild_config(self, guild_id: int, *, connection=None) -> Optional[Config]:
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1;"
    conn = connection or self.bot.pool
    record = await conn.fetchrow(query, str(guild_id))
    log.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
    if record is not None:
      return Config(record=record, bot=self.bot)
    return None

  @cache.cache()
  async def get_reddit_post(self, query: str) -> RedditMedia:
    return await RedditMedia.no_context(self.bot, query)

  async def cog_command_error(self, ctx: MyContext, error: commands.CommandError):
    just_send = (MustBeAuthor, NotRedditLink,)
    error = getattr(error, 'original', error)

    if isinstance(error, just_send):
      await ctx.send(embed=embed(title=str(error), color=MessageColors.error()))
    else:
      raise error

  @commands.Cog.listener()
  async def on_message(self, message: discord.Message):
    if message.author.bot and message.author.id != 892865928520413245:
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

    reg = re.findall(PATTERN, message.content)

    if len(reg) != 1:
      return

    ctx: MyContext = await self.bot.get_context(message, cls=MyContext)
    if ctx.command is not None:
      return

    config = await self.get_guild_config(message.guild.id, connection=ctx.db)
    if config is None or not config.enabled:
      return

    try:
      assert await self.get_reddit_post(reg[0])
    except BaseException:
      return

    try:
      await message.add_reaction(self.emoji)
    except (discord.Forbidden, discord.NotFound):
      pass

  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
    if payload.emoji.name != self.emoji or payload.member and payload.member.bot or not payload.guild_id:
      return
    channel = self.bot.get_channel(payload.channel_id)
    if not channel:
      return
    if isinstance(channel, (discord.StageChannel, discord.ForumChannel, discord.CategoryChannel, discord.abc.PrivateChannel)):
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
    # guild = self.bot.get_guild(payload.guild_id)
    async with channel.typing():
      try:
        redditlinkmedia = await self.get_reddit_post(message.content)
        thing = await self.extract(message.channel, redditlinkmedia)
        # thing = await self.extract(message.content, payload=payload, guild=guild, channel=channel, message=message)
        await message.reply(**thing, mention_author=False)
      except discord.HTTPException:
        try:
          await message.channel.send(**thing, mention_author=False)  # type: ignore
        except discord.HTTPException:
          pass
      except Exception as e:
        await message.reply(embed=embed(title="Something went wrong", description="Please try again later. I have notified my boss of this error", color=MessageColors.error()), mention_author=False)
        raise e

  @commands.group(name="redditextract", help="Extracts the media from the reddit post", invoke_without_command=True, case_insensitive=True)
  async def norm_extract(self, ctx: MyContext, link: RedditMedia):
    await ctx.release()
    if ctx.interaction:
      await ctx.defer()
    async with ctx.typing():
      extracted = await self.extract(ctx.channel, link)

    await ctx.send(**extracted)

  @norm_extract.command("enable", help="Enable or disabled Friday's reddit link extraction. (When disabled Friday won't react to reddit links.)")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_messages=True)
  @commands.bot_has_permissions(add_reactions=True)
  async def extract_toggle(self, ctx: GuildContext, enable: bool):
    await ctx.db.execute("UPDATE servers SET reddit_extract=$1 WHERE id=$2", enable, str(ctx.guild.id))
    self.get_guild_config.invalidate(self, ctx.guild.id)
    if enable:
      return await ctx.send(embed=embed(title="I will now react to Reddit links", description="For me to then extract a reddit link the author of the message must react with the same emoji Friday did.\nFriday also requires add_reaction permissions (if not already) for this to work."))
    await ctx.send(embed=embed(title="I will no longer react to Reddit links.", description="The Reddit extract commands will still work."))

  async def extract(self, channel: discord.abc.MessageableChannel, reddit: RedditMedia) -> dict:
    filesize = 8388608
    if channel.guild is not None:
      filesize = channel.guild and channel.guild.filesize_limit or filesize

    nsfw = channel.nsfw if channel is not None and not isinstance(channel, discord.Thread) else channel.parent.nsfw if channel is not None else False  # type: ignore
    spoiler = not ((nsfw is True and reddit.submission.over_18 is True) or (nsfw is False and reddit.submission.over_18 is False) or (nsfw is True and reddit.submission.over_18 is False))

    if reddit.needs_extraction:
      try:
        async with self.extract_lock:
          linkdata = await self.bot.loop.run_in_executor(None, ytdl.extract_info, reddit.url)
      except youtube_dl.DownloadError as e:
        raise commands.BadArgument(f"Could not extract the link: {e}")
      if 'entries' in linkdata:
        # take first item from a playlist
        linkdata = linkdata['entries'][0]

      thispath = os.getcwd()
      if "\\" in thispath:
        seperator = "\\\\"
      else:
        seperator = "/"
      mp4file = f'{thispath}{seperator}{linkdata["extractor"]}-{linkdata["id"]}-{linkdata["title"]}.webm'
      try:
        # name = f'{linkdata["extractor"]}-{linkdata["id"]}-{linkdata["title"]}.{linkdata["ext"]}'
        name = reddit.submission.title.split()
        return dict(file=discord.File(fp=mp4file, filename=f'friday-bot.com_{"_".join(name)}.mp4', spoiler=spoiler))
      except discord.HTTPException:
        return dict(embed=embed(title="This file is too powerful to be uploaded", description="You will have to open reddit to view this", color=MessageColors.error()))
      finally:
        try:
          os.remove(mp4file)
        except PermissionError:
          pass
    else:
      if spoiler is True:
        return dict(content=f"||{reddit.url}||")
      else:
        return dict(content=reddit.url)


async def setup(bot):
  await bot.add_cog(redditlink(bot))
