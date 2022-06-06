from __future__ import annotations

import asyncio
import datetime
import functools
import os
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, ClassVar, List, Optional, Union

import asyncpg
import discord
import openai
import validators
from discord.app_commands.checks import Cooldown
from discord.ext import commands
from google.cloud import translate_v2 as translate
from six.moves.html_parser import HTMLParser  # type: ignore
from slugify import slugify

from functions import (MessageColors, MyContext, cache, checks, embed,
                       relay_info, time)
from functions.config import PremiumTiersNew

if TYPE_CHECKING:
  from typing_extensions import Self

  from cogs.patreons import Patreons
  from functions.custom_contexts import GuildContext
  from index import Friday


openai.api_key = os.environ["OPENAI"]

POSSIBLE_SENSITIVE_MESSAGE = "*Possibly sensitive:* ||"
POSSIBLE_OFFENSIVE_MESSAGE = "**I failed to respond because my message might have been offensive, please choose another topic or try again**"

PERSONAS = [("🥰", "default", "Fridays default persona"), ("🏴‍☠️", "pirate", "Friday becomes one with the sea")]


class ChatError(commands.CheckFailure):
  pass


class Config:
  __slots__ = ("bot", "id", "chat_channel_id", "persona", "lang", "tier", "puser",
               )

  bot: Friday
  id: int
  chat_channel_id: Optional[int]
  tier: int
  puser: Optional[int]
  persona: Optional[str]
  lang: str

  @classmethod
  async def from_record(cls, record: asyncpg.Record, bot: Friday) -> Self:
    self = cls()

    self.bot = bot
    self.id = int(record["id"], base=10)
    self.chat_channel_id = record.get("chatchannel") and int(record["chatchannel"], base=10)
    self.tier = record["tier"] if record else 0
    self.puser = record["user_id"] if record else None
    self.persona = record["persona"]
    self.lang = record["lang"] or "en"
    return self

  @property
  def chat_channel(self) -> Optional[Union[discord.TextChannel, discord.VoiceChannel, discord.Thread]]:
    if self.chat_channel_id:
      guild = self.bot.get_guild(self.id)
      return guild and guild.get_channel(self.chat_channel_id)  # type: ignore


class UserConfig:
  __slots__ = ("bot", "user_id", "tier", "guild_ids",)

  bot: Friday
  user_id: int
  tier: int
  guild_ids: List[int]

  @classmethod
  async def from_record(cls, record: asyncpg.Record, bot: Friday) -> Self:
    self = cls()

    self.bot = bot
    self.user_id = int(record["user_id"], base=10)
    self.tier = record["tier"] if record else 0
    self.guild_ids = record["guild_ids"] or []
    return self


class SpamChecker:
  def __init__(self):
    self._absolute_minute = commands.CooldownMapping.from_cooldown(6, 30, commands.BucketType.user)
    self._absolute_hour = commands.CooldownMapping.from_cooldown(180, 3600, commands.BucketType.user)
    self._free = commands.CooldownMapping.from_cooldown(30, 43200, commands.BucketType.user)
    self._voted = commands.CooldownMapping.from_cooldown(60, 43200, commands.BucketType.user)
    self._patron = commands.CooldownMapping.from_cooldown(100, 43200, commands.BucketType.user)

  def is_spamming(self, msg: discord.Message, tier: int, voted: bool) -> tuple[bool, Optional[Cooldown], Optional[str]]:
    current = msg.created_at.timestamp()

    min_bucket = self._absolute_minute.get_bucket(msg)
    hour_bucket = self._absolute_hour.get_bucket(msg)
    free_bucket = self._free.get_bucket(msg)
    voted_bucket = self._voted.get_bucket(msg)
    patron_bucket = self._patron.get_bucket(msg)

    min_rate = min_bucket.update_rate_limit(current)
    hour_rate = hour_bucket.update_rate_limit(current)
    free_rate = free_bucket.update_rate_limit(current)
    voted_rate = voted_bucket.update_rate_limit(current)
    patron_rate = patron_bucket.update_rate_limit(current)

    if min_rate:
      return True, min_bucket, None

    if hour_rate:
      return True, hour_bucket, None

    if free_rate and not voted and not tier >= PremiumTiersNew.tier_1.value:
      return True, free_bucket, "free"

    if voted_rate and voted and tier < PremiumTiersNew.tier_1.value:
      return True, voted_bucket, "voted"

    if patron_rate and tier >= PremiumTiersNew.tier_1.value:
      return True, patron_bucket, "patron"

    return False, None, None


class ChatHistory:
  _limit: ClassVar[int] = 3
  _messages_per_group: ClassVar[int] = 2

  def __init__(self):
    self.lock = asyncio.Lock()
    self._history: List[str] = []
    self._bot_name: str = "Friday"

  def __repr__(self) -> str:
    return f"<Chathistory len={len(self.history())}>"

  def __str__(self) -> str:
    return "\n".join(self.history())

  def __len__(self) -> int:
    return len("\n".join(self.history()))

  def history(self, *, limit=_limit) -> list:
    return self._history[::-1][:limit * self._messages_per_group][::-1]

  def bot_repeating(self, *, limit=_limit) -> bool:
    bot_messages = [item for item in self.history(limit=limit) if item.startswith(f"{self._bot_name}: ")][::-1] or []
    repeats = [item for x, item in enumerate(bot_messages) if item == bot_messages[x - 1]]
    repeats = [*repeats, repeats[0]] if len(repeats) > 0 else repeats
    return bool(repeats and len(repeats) >= 3)

  def banned_nickname(self, name: str) -> str:
    banned = ["nigger", "nigg"]
    string = slugify(name).replace("-", "")
    for old, new in (("4", "a"), ("@", "a"), ("3", "e"), ("1", "i"), ("0", "o"), ("7", "t"), ("5", "s")):
      string = string.replace(old, new)
    return name if string.lower() not in banned else "Cat"

  async def prompt(self, user_content: str, user_name: str, bot_name: str = "Friday", *, limit=_limit) -> str:
    async with self.lock:
      while len(self._history) > limit * self._messages_per_group:
        self._history.pop(0)
      return '\n'.join(self.history(limit=limit)) + ("\n" if len(self.history(limit=limit)) > 0 else "") + f"{user_name}: {user_content}\n{bot_name}:"

  async def add_message(self, msg: discord.Message, bot_content: str, *, user_content: str = None, user_name: str = None, bot_name: str = None):
    async with self.lock:
      bot_seperator = "" if bot_content.startswith(" ") else " "
      user_content = user_content or msg.clean_content
      user_seperator = "" if user_content.startswith(" ") else " "
      user_name = user_name or msg.author.display_name
      self._bot_name = bot_name = bot_name or msg.guild and msg.guild.me.display_name or "Friday"

      to_add_user = f"{self.banned_nickname(user_name)}:{user_seperator}{user_content}"
      to_add_bot = f"{self.banned_nickname(bot_name)}:{bot_seperator}{bot_content}"
      self._history.append(to_add_user)
      self._history.append(to_add_bot)


class CooldownByRepeating(commands.CooldownMapping):
  def _bucket_key(self, msg):
    return (msg.content)


class Translation:
  text: str
  translatedText: str
  input: str
  detectedSourceLanguage: Optional[str]

  @classmethod
  async def from_text(cls, text: str, from_lang: str = None, to_lang: str = "en", *, parent: Chat) -> Self:
    self = cls()

    self.text = text
    self.translatedText = text
    self.input = text
    self.detectedSourceLanguage = from_lang
    if from_lang != to_lang and from_lang != "ep" and to_lang != "ep":
      try:
        trans_func = functools.partial(parent.translate_client.translate, source_language=from_lang, target_language=to_lang)
        translation = await parent.bot.loop.run_in_executor(None, trans_func, text)
        self.input = translation.get("input", text)
        self.detectedSourceLanguage = translation.get("detectedSourceLanguage", from_lang)
        if translation is not None and translation.get("translatedText", None) is not None:
          self.translatedText = parent.h.unescape(translation["translatedText"])  # type: ignore
      except OSError:
        pass

    return self

  def __str__(self) -> str:
    return self.translatedText if self.translatedText is not None else self.text


class Chat(commands.Cog):
  """Chat with Friday, say something on Friday's behalf, and more with the chat commands."""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot
    self.translate_client = translate.Client()  # _http=self.bot.http)
    self.h = HTMLParser()

    self.api_lock = asyncio.Semaphore(3)

    self._spam_check = SpamChecker()
    self._repeating_spam = CooldownByRepeating.from_cooldown(3, 60 * 3, commands.BucketType.channel)

    # channel_id: list
    self.chat_history: defaultdict[int, ChatHistory] = defaultdict(lambda: ChatHistory())

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @cache.cache()
  async def get_guild_config(self, guild_id: int, *, connection: Optional[asyncpg.Connection] = None) -> Optional[Config]:
    query = """SELECT *
    FROM servers s
    LEFT OUTER JOIN patrons p
      ON s.id = ANY(p.guild_ids)
    WHERE s.id=$1"""
    conn = connection or self.bot.pool
    try:
      record = await conn.fetchrow(query, str(guild_id))
    except Exception as e:
      raise e
    else:
      self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
      if record is not None:
        return await Config.from_record(record, self.bot)
    return None

  @commands.Cog.listener()
  async def on_invalidate_patreon(self, guild_id: int):
    self.get_guild_config.invalidate(self, guild_id)

  @commands.command(name="say", aliases=["repeat"], help="Make Friday say what ever you want")
  async def say(self, ctx: MyContext, *, content: str):
    if content in ("im stupid", "i'm stupid", "i am dumb", "im dumb"):
      return await ctx.reply("yeah we know", allowed_mentions=discord.AllowedMentions.none())
    await ctx.reply(content, allowed_mentions=discord.AllowedMentions.none())

  @commands.group("chat", invoke_without_command=True)
  async def chat(self, ctx: MyContext, *, message: str):
    """Chat with Friday powered by GPT-3 and get a response."""
    await self.chat_message(ctx, content=message)

  @chat.error
  async def chat_error(self, ctx: MyContext, error: commands.CommandError):
    if isinstance(error, ChatError):
      await ctx.send(embed=embed(title=str(error), color=MessageColors.error()))

  @chat.command("info")
  async def chat_info(self, ctx: MyContext):
    """Displays information about the current conversation."""
    free_rate = self._spam_check._free.get_bucket(ctx.message).get_tokens(ctx.message.created_at.timestamp())
    voted_rate = self._spam_check._voted.get_bucket(ctx.message).get_tokens(ctx.message.created_at.timestamp())
    patroned_rate = self._spam_check._patron.get_bucket(ctx.message).get_tokens(ctx.message.created_at.timestamp())
    history = self.chat_history[ctx.channel.id]
    content = history and str(history) or "No history"
    await ctx.send(embed=embed(
        title="Chat Info",
        fieldstitle=["Messages", "Voted messages", "Patroned messages", "Recent history resets", "Message History"],
        fieldsval=[f"{free_rate} remaining", f"{voted_rate} remaining", f"{patroned_rate} remaining", str(self.bot.chat_repeat_counter[ctx.channel.id]), f"```\n{content}\n```"],
        fieldsin=[True, True, True, False, False]
    ))

  @commands.command(name="reset", help="Resets Friday's chat history. Helps if Friday is repeating messages")
  async def reset_history(self, ctx: MyContext):
    try:
      self.chat_history.pop(ctx.channel.id)
    except KeyError:
      await ctx.send(embed=embed(title="No history to delete"))
    except Exception as e:
      raise e
    else:
      self.bot.chat_repeat_counter[ctx.channel.id] += 1
      await ctx.send(embed=embed(title="My chat history has been reset", description="I have forgotten the last few messages"))

  @commands.group(name="chatchannel", extras={"examples": ["#channel"]}, invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def chatchannel(self, ctx: GuildContext, channel: discord.TextChannel = None):
    """Set the current channel so that I will always try to respond with something"""
    if channel is None:
      config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
      return await ctx.send(embed=embed(title="Current chat channel", description=f"{config and config.chat_channel and config.chat_channel.mention}"))

    await ctx.db.execute("UPDATE servers SET chatchannel=$1 WHERE id=$2", str(channel.id), str(ctx.guild.id))
    await ctx.send(embed=embed(title="Chat channel set", description=f"I will now respond to every message in this channel\n{channel.mention}"))

  @chatchannel.command(name="clear", help="Clear the current chat channel")
  @commands.guild_only()
  @commands.has_guild_permissions(manage_channels=True)
  async def chatchannel_clear(self, ctx: GuildContext):
    await ctx.db.execute("UPDATE servers SET chatchannel=NULL WHERE id=$1", str(ctx.guild.id))
    await ctx.send(embed=embed(title="Chat channel cleared", description="I will no longer respond to messages in this channel"))

  @commands.command(name="persona", help="Change Friday's persona")
  @commands.guild_only()
  @checks.is_mod_and_min_tier(tier=PremiumTiersNew.tier_1.value, manage_channels=True)
  async def persona(self, ctx: GuildContext):
    current = await ctx.pool.fetchval("SELECT persona FROM servers WHERE id=$1", str(ctx.guild.id))
    choice = await ctx.multi_select("Please select a new persona", [p.capitalize() for _, p, _ in PERSONAS], values=[p for _, p, _ in PERSONAS], emojis=[e for e, _, _ in PERSONAS], descriptions=[d for _, _, d in PERSONAS], default=current, placeholder=f"Current: {current.capitalize()}")
    if choice is None:
      return await ctx.send(embed=embed(title="No change made"))

    await ctx.db.execute("UPDATE servers SET persona=$1 WHERE id=$2", choice[0], str(ctx.guild.id))
    await ctx.send(embed=embed(title=f"New Persona `{choice[0].capitalize()}`"))

  @chatchannel.after_invoke
  @persona.after_invoke
  async def settings_after_invoke(self, ctx: GuildContext):
    if not ctx.guild:
      return

    self.get_guild_config.invalidate(self, ctx.guild.id)

  @cache.cache(maxsize=1024)
  async def content_filter_check(self, text: str, user_id: str) -> Optional[int]:
    if self.bot.testing:
      return 0
    try:
      async with self.api_lock:
        response = await self.bot.loop.run_in_executor(
              None,
              functools.partial(
                  lambda: openai.Completion.create(
                      engine="content-filter-alpha",
                      prompt=f"<|endoftext|>{text}\n--\nLabel:",
                      temperature=0,
                      max_tokens=1,
                      top_p=1,
                      frequency_penalty=0,
                      presence_penalty=0,
                      user=user_id,
                      logprobs=10
                  )))
    except Exception as e:
      raise e
    # print(response)
    if response is None:
      return None
    toxic_therhold = -0.355
    output_label = response["choices"][0]["text"]
    if output_label == "2":
      logprobs = response["choices"][0]["logprobs"]["top_logprobs"][0]
      if logprobs["2"] < toxic_therhold:
        logprob_0 = logprobs.get("0", None)
        logprob_1 = logprobs.get("1", None)
        if logprob_0 is not None and logprob_1 is not None:
          output_label = "0" if logprob_0 >= logprob_1 else "1"
        elif logprob_0 is not None:
          output_label = "0"
        elif logprob_1 is not None:
          output_label = "1"
    if output_label not in ["0", "1", "2"]:
      output_label = "2"
    return int(output_label)

  async def openai_req(self, msg: discord.Message, current_tier: int, persona: str = None, *, content: str = None) -> Optional[str]:
    content = content or msg.clean_content
    author_prompt_name, my_prompt_name = msg.author.display_name, "Friday"
    my_prompt_name = msg.guild.me.display_name if msg.guild else self.bot.user.name
    prompt = await self.chat_history[msg.channel.id].prompt(content, author_prompt_name, my_prompt_name, limit=5 if current_tier >= PremiumTiersNew.tier_1.value else 3)
    engine = os.environ["OPENAIMODEL"]
    if persona and persona == "pirate":
      engine = os.environ["OPENAIMODELPIRATE"]
    if self.bot.testing:
      return "This message is a test"
    try:
      async with self.api_lock:
        response = await self.bot.loop.run_in_executor(
            None,
            functools.partial(
                lambda: openai.Completion.create(
                    model=engine,
                    prompt=prompt,
                    temperature=0.8,
                    max_tokens=25 if not current_tier >= PremiumTiersNew.tier_1.value else 50,
                    top_p=0.9,
                    user=str(msg.channel.id),
                    frequency_penalty=1.5,
                    presence_penalty=1.5,
                    stop=[f"\n{author_prompt_name}:", f"\n{my_prompt_name}:", "\n", "\n###\n"]
                )))
    except Exception as e:
      raise e
    else:
      return response.get("choices")[0].get("text").replace("\n", "") if response is not None else None

  @commands.Cog.listener()
  async def on_message(self, msg: discord.Message):
    await self.bot.wait_until_ready()

    if msg.author.bot and msg.author.id != 892865928520413245:
      return

    if msg.clean_content == "" or msg.activity is not None:
      return

    if msg.clean_content.lower().startswith(tuple(self.bot.log.get_prefixes())):
      return

    if not hasattr(msg.type, "name") or (msg.type.name != "default" and msg.type.name != "reply"):
      return

    if msg.author.id in self.bot.blacklist:
      return

    if msg.guild is not None and msg.guild.id in self.bot.blacklist:
      return

    ctx = await self.bot.get_context(msg, cls=MyContext)
    if ctx.command is not None or msg.webhook_id is not None:
      return

    valid = validators.url(msg.clean_content)
    if valid:
      return

    try:
      # await self.answer_message(msg)
      await self.chat_message(ctx)
    except ChatError:
      pass
    finally:
      await ctx.release()

  async def chat_message(self, ctx: MyContext | GuildContext, *, content: str = None):
    msg = ctx.message
    content = content or msg.clean_content
    current_tier = PremiumTiersNew.free.value

    config = None
    if ctx.guild:
      log = self.bot.log
      if log:
        conf = await log.get_guild_config(ctx.guild.id, connection=ctx.db)
        if not conf:
          await ctx.db.execute(f"INSERT INTO servers (id,lang) VALUES ({str(ctx.guild.id)},'{ctx.guild.preferred_locale.value.split('-')[0]}') ON CONFLICT DO NOTHING")
          log.get_guild_config.invalidate(log, ctx.guild.id)
          self.get_guild_config.invalidate(self, ctx.guild.id)
          conf = await log.get_guild_config(ctx.guild.id, connection=ctx.db)
        if "chat" in conf.disabled_commands:
          return

      config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
      if config is None:
        self.bot.logger.error(f"Config was not available in chat for (guild: {ctx.guild.id if ctx.guild else None}) (channel type: {ctx.channel.type if ctx.channel else 'uhm'}) (user: {msg.author.id})")
        raise ChatError("Guild config not available, please contact developer.")

      if not ctx.command:
        chat_channel = config.chat_channel
        if chat_channel is not None and ctx.channel != chat_channel:
          if ctx.guild.me not in msg.mentions:
            return
        elif chat_channel is None and ctx.guild.me not in msg.mentions:
          return

      if config.tier:
        current_tier = config.tier
    lang = ctx.guild and config and config.lang or "en"

    voted = await checks.user_voted(self.bot, ctx.author, connection=ctx.db)

    if voted and not current_tier > PremiumTiersNew.voted.value:
      current_tier = PremiumTiersNew.voted.value

    patron_cog: Optional[Patreons] = self.bot.get_cog("Patreons")  # type: ignore
    if patron_cog is not None:
      patrons = await patron_cog.get_patrons(connection=ctx.db)

      patron = next((p for p in patrons if p.id == ctx.author.id), None)

      if patron is not None:
        current_tier = patron.tier if patron.tier > current_tier else current_tier

    char_count = len(content)
    max_content = 100 if current_tier == PremiumTiersNew.free.value else 200
    if char_count > max_content:
      raise ChatError(f"Message is too long. Max length is {max_content} characters.")

    # Anything to do with sending messages needs to be below the above check
    response = None
    is_spamming, rate_limiter, rate_name = self._spam_check.is_spamming(msg, current_tier, voted)
    resp = None
    if is_spamming and rate_limiter:
      vote_advertise = bool(rate_name == "free" and not voted)
      patreon_advertise = bool(rate_name == "voted" and not (current_tier >= PremiumTiersNew.tier_1.value))
      retry_after = discord.utils.utcnow() + datetime.timedelta(seconds=rate_limiter.get_retry_after())
      self.bot.logger.info(f"{msg.author} ({msg.author.id}) is being ratelimited at over {rate_limiter.rate} messages and can retry after {time.human_timedelta(retry_after, accuracy=2, brief=True)}")
      ad_message = "If you would like to send me more messages you can get more by voting at https://top.gg/bot/476303446547365891/vote" if vote_advertise else "If you would like to send even more messages please support Friday on Patreon at https://patreon.com/join/fridaybot" if patreon_advertise else ""
      resp = await ctx.reply(embed=embed(title=f"You have sent me over `{rate_limiter.rate}` messages in that last `{rate_limiter.per} seconds` and are being rate limited, try again <t:{int(retry_after.timestamp())}:R>", description=ad_message, color=MessageColors.error()), mention_author=False)
      return
    chat_history = self.chat_history[msg.channel.id]
    async with ctx.typing():
      translation = await Translation.from_text(content, from_lang=lang, parent=self)
      try:
        response = await self.openai_req(msg, current_tier, config and config.persona, content=str(translation).strip('\n'))
      except Exception as e:
        # resp = await ctx.send(embed=embed(title="", color=MessageColors.error()))
        self.bot.dispatch("chat_completion", msg, resp, True, filtered=None, prompt="\n".join(chat_history.history(limit=5 if current_tier >= PremiumTiersNew.tier_1.value else 3)))
        raise ChatError("Something went wrong, please try again later") from e
      if response is None or response == "":
        raise ChatError("Somehow, I don't know what to say.")
      await chat_history.add_message(msg, response, user_content=content)
      content_filter = await self.content_filter_check(response, str(msg.channel.id))
    if translation is not None and translation.detectedSourceLanguage != "en" and response is not None and "dynamic" not in response:
      chars_to_strip = "?!,;'\":`"
      final_translation = await Translation.from_text(response.replace("dynamic", ""), from_lang="en", to_lang=str(translation.detectedSourceLanguage) if translation.translatedText.strip(chars_to_strip).lower() != translation.input.strip(chars_to_strip).lower() else "en", parent=self)
      response = str(final_translation)

    if content_filter != 2:
      resp = await ctx.reply(content=response if content_filter == 0 else f"{POSSIBLE_SENSITIVE_MESSAGE}{response}||", allowed_mentions=discord.AllowedMentions.none(), mention_author=False)
      await relay_info(f"{PremiumTiersNew(current_tier)} - **{ctx.author.name}:** {content}\n**Me:** {response}", self.bot, webhook=self.bot.log.log_chat)
    elif content_filter == 2:
      resp = await ctx.reply(content=POSSIBLE_OFFENSIVE_MESSAGE, mention_author=False)
      await relay_info(f"{PremiumTiersNew(current_tier)} - **{ctx.author.name}:** {content}\n**Me:** Possible offensive message: {response}", self.bot, webhook=self.bot.log.log_chat)
    self.bot.dispatch("chat_completion", msg, resp, False, filtered=content_filter, persona=msg.guild and config and config.persona, prompt="\n".join(self.chat_history[msg.channel.id].history(limit=5 if current_tier >= PremiumTiersNew.tier_1.value else 3)))

    async with chat_history.lock:
      if chat_history.bot_repeating():
        self.chat_history.pop(ctx.channel.id)
        self.bot.chat_repeat_counter[msg.channel.id] += 1
        self.bot.logger.info("Popped chat history for channel #{}".format(ctx.channel))

  # async def check_for_answer_questions(self, msg: discord.Message, min_tiers: list) -> bool:
  #   if msg.author.bot:
  #     return False
  #   if (len(msg.clean_content) > 100 and not min_tiers["min_g_t1"]) or (len(msg.clean_content) > 200 and min_tiers["min_g_t1"]):
  #     return False
  #   if msg.guild is not None:
  #     if self.bot.log.get_guild_chat_channel(msg.guild) != msg.channel.id:
  #       if msg.guild.me not in msg.mentions:
  #         return False
  #   # if msg.guild is not None:
  #   #   muted = self.bot.log.get_guild_muted(msg.guild)
  #   #   if muted == 1 or muted is True:
  #   #     return False
  #   # if not await self.global_chat_checks(msg):
  #   #   return False
  #   bucket_minute, bucket_hour = self.spam_control_minute.get_bucket(msg), self.spam_control_hour.get_bucket(msg)
  #   current = msg.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()
  #   retry_after_minute, retry_after_hour = bucket_minute.update_rate_limit(current), bucket_hour.update_rate_limit(current)
  #   if (retry_after_minute or retry_after_hour):  # and msg.author.id != self.bot.owner_id:
  #     raise commands.CommandOnCooldown(bucket_minute, retry_after_minute)
  #     return False
  #   return True

  # async def search_questions(self, msg: discord.Message) -> str:
  #   return ""


async def setup(bot):
  if not hasattr(bot, "cluster"):
    bot.cluster = None

  if bot.cluster and not hasattr(bot.cluster.launcher, "api_lock"):
    bot.cluster.launcher.api_lock = asyncio.Semaphore(3)

  if not hasattr(bot, "chat_repeat_counter"):
    bot.chat_repeat_counter = Counter()

  await bot.add_cog(Chat(bot))
