import datetime
import os
import functools
from collections import defaultdict
from typing import Optional, Union

import discord
import openai
import validators
from google.cloud import translate_v2 as translate
from discord.ext import commands
from six.moves.html_parser import HTMLParser
from typing_extensions import TYPE_CHECKING

from functions import (MessageColors, MyContext, cache, checks, embed, config as function_config,
                       relay_info)

if TYPE_CHECKING:
  from index import Friday as Bot

openai.api_key = os.environ.get("OPENAI")

POSSIBLE_SENSITIVE_MESSAGE = "*Possibly sensitive:* ||"
POSSIBLE_OFFENSIVE_MESSAGE = "**I failed to respond because my message might have been offensive, please choose another topic or try again**"


class Config:
  __slots__ = ("bot", "id", "chat_channel_id", "persona", "lang", "tier", "puser",)

  @classmethod
  async def from_record(cls, record, precord, bot):
    self = cls()

    self.bot = bot
    self.id: int = int(record["id"], base=10)
    self.chat_channel_id: Optional[int] = int(record["chatchannel"], base=10) if record["chatchannel"] else None
    self.tier: int = precord["tier"] if precord else 0
    self.puser: str = precord["user_id"] if precord else None
    self.persona: Optional[str] = record["persona"]
    self.lang: str = record["lang"] or "en"
    return self

  @property
  def chat_channel(self):
    guild = self.bot.get_guild(self.id)
    return guild and self.chat_channel_id and guild.get_channel(self.chat_channel_id)


class UserConfig:
  __slots__ = ("bot", "user_id", "tier", "guild_ids",)

  @classmethod
  async def from_record(cls, record, bot):
    self = cls()

    self.bot = bot
    self.user_id: int = int(record["user_id"], base=10)
    self.tier: int = record["tier"] if record else 0
    self.guild_ids: list = record["guild_ids"] or []
    return self


class SpamChecker:
  def __init__(self):
    self.absolute_minute = commands.CooldownMapping.from_cooldown(6, 30, commands.BucketType.user)
    self.absolute_hour = commands.CooldownMapping.from_cooldown(180, 3600, commands.BucketType.user)
    self.free = commands.CooldownMapping.from_cooldown(80, 43200, commands.BucketType.user)
    self.voted = commands.CooldownMapping.from_cooldown(200, 43200, commands.BucketType.user)

  def triggered(self, msg: discord.Message) -> Optional[commands.Cooldown]:
    if self.absolute_hour.get_bucket(msg).get_tokens() == 0:
      return self.absolute_hour.get_bucket(msg)
    elif self.absolute_minute.get_bucket(msg).get_tokens() == 0:
      return self.absolute_minute.get_bucket(msg)
    elif self.voted.get_bucket(msg).get_tokens() == 0:
      return self.voted.get_bucket(msg)
    elif self.free.get_bucket(msg).get_tokens() == 0:
      return self.free.get_bucket(msg)
    return None

  def get_triggered_rate(self, msg: discord.Message) -> Optional[float]:
    trig = self.triggered(msg)
    if trig is None:
      return None
    return trig.rate

  def get_triggered_per(self, msg: discord.Message) -> Optional[float]:
    trig = self.triggered(msg)
    if trig is None:
      return None
    return trig.per

  def is_abs_min_spam(self, msg: discord.Message) -> bool:
    if msg.guild is None:
      return False
    current = msg.created_at.timestamp()

    bucket = self.absolute_minute.get_bucket(msg)
    if bucket.update_rate_limit(current):
      return True
    return False

  def is_abs_hour_spam(self, msg: discord.Message) -> bool:
    if msg.guild is None:
      return False
    current = msg.created_at.timestamp()

    bucket = self.absolute_hour.get_bucket(msg)
    if bucket.update_rate_limit(current):
      return True
    return False

  def is_free_spam(self, msg: discord.Message) -> bool:
    if msg.guild is None:
      return False
    current = msg.created_at.timestamp()

    bucket = self.free.get_bucket(msg)
    if bucket.update_rate_limit(current):
      return True
    return False

  def is_voted_spam(self, msg: discord.Message) -> bool:
    if msg.guild is None:
      return False
    current = msg.created_at.timestamp()

    bucket = self.voted.get_bucket(msg)
    if bucket.update_rate_limit(current):
      return True
    return False


class Translation:
  @classmethod
  async def from_text(cls, text: str, from_lang: str = None, to_lang: str = "en", *, parent: "Chat"):
    self = cls()

    self.text: str = text
    self.translatedText: str = text
    self.input: str = text
    self.detectedSourceLanguage: str = from_lang
    if from_lang != to_lang:
      try:
        trans_func = functools.partial(parent.translate_client.translate, source_language=from_lang, target_language=to_lang)
        translation = await parent.bot.loop.run_in_executor(None, trans_func, text)
        self.input = translation.get("input", text)
        self.detectedSourceLanguage = translation.get("detectedSourceLanguage", from_lang)
        if translation is not None and translation.get("translatedText", None) is not None:
          self.translatedText = parent.h.unescape(translation["translatedText"])
      except OSError:
        pass

    return self

  def __str__(self) -> str:
    return self.translatedText if self.translatedText is not None else self.text


class Chat(commands.Cog):
  """Chat with Friday, say something on Friday's behalf, and more with the chat commands."""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.translate_client = translate.Client()  # _http=self.bot.http)
    self.h = HTMLParser()

    self._spam_check = defaultdict(SpamChecker)

    # channel_id: list
    self.chat_history = defaultdict(lambda: [])

  def __repr__(self):
    return "<cogs.Chat>"

  @cache.cache()
  async def get_guild_config(self, guild_id: int) -> Optional[Config]:
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1;"
    pquery = "SELECT * FROM patrons WHERE $1::text = ANY(guild_ids) LIMIT 1;"
    async with self.bot.db.pool.acquire(timeout=300.0) as conn:
      record = await conn.fetchrow(query, str(guild_id))
      precord = await conn.fetchrow(pquery, str(guild_id))
      self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
      self.bot.logger.debug(f"PostgreSQL Query: \"{pquery}\" + {str(guild_id)}")
      if record is not None:
        return await Config.from_record(record, precord, self.bot)
      return None

  @cache.cache()
  async def get_user_patron_config(self, user_id: int) -> Optional[UserConfig]:
    query = "SELECT * FROM patrons WHERE user_id=$1 LIMIT 1;"
    async with self.bot.db.pool.acquire(timeout=300.0) as conn:
      record = await conn.fetchrow(query, str(user_id))
      self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {str(user_id)}")
      if record is not None:
        return await UserConfig.from_record(record, self.bot)
      return None

  @commands.Cog.listener()
  async def on_invalidate_patreon(self, guild_id: int, user_id: int):
    self.get_guild_config.invalidate(self, guild_id)
    self.get_user_patron_config.invalidate(self, user_id)

  @commands.command(name="say", aliases=["repeat"], help="Make Friday say what ever you want")
  async def say(self, ctx: "MyContext", *, content: str):
    if content in ("im stupid", "i'm stupid", "i am dumb", "im dumb"):
      return await ctx.reply("yeah we know", allowed_mentions=discord.AllowedMentions.none())
    await ctx.reply(content, allowed_mentions=discord.AllowedMentions.none())

  @commands.command(name="reset", help="Resets Friday's chat history. Helps if Friday is repeating messages")
  async def reset_history(self, ctx: "MyContext"):
    try:
      self.chat_history.pop(ctx.channel.id)
    except KeyError:
      await ctx.send(embed=embed(title="No history to delete"))
    except Exception as e:
      raise e
    else:
      await ctx.send(embed=embed(title="My chat history has been reset", description="I have forgotten the last few messages"))

  async def fetch_message_history(self, channel: discord.TextChannel, *, message_limit: int = 15, current_tier: int) -> str:
    my_prompt_name = channel.guild.me.display_name if hasattr(channel, "guild") and channel.guild is not None else self.bot.user.name
    history = self.chat_history[channel.id]
    if len(history) > 6:
      history = self.chat_history[channel.id] = self.chat_history[channel.id][:7]
    prompt = "\n".join(reversed(history))

    return prompt + f"\n{my_prompt_name}:"

  async def content_filter_check(self, text: str, user_id: str):
    try:
      response = openai.Completion.create(
          engine="content-filter-alpha-c4",
          prompt=f"<|endoftext|>{text}\n--\nLabel:",
          temperature=0,
          max_tokens=1,
          top_p=1,
          frequency_penalty=0,
          presence_penalty=0,
          user=user_id,
          logprobs=10
      )
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
          if logprob_0 >= logprob_1:
            output_label = "0"
          else:
            output_label = "1"
        elif logprob_0 is not None:
          output_label = "0"
        elif logprob_1 is not None:
          output_label = "1"
    if output_label not in ["0", "1", "2"]:
      output_label = "2"
    return int(output_label)

  async def openai_req(self, channel: discord.TextChannel, author: Union[discord.User, discord.Member], content: str, current_tier: int):
    author_prompt_name, prompt, my_prompt_name = author.display_name, "", "Friday"
    prompt = await self.fetch_message_history(channel, current_tier=current_tier)
    # Fix this when get more patrons
    # if min_tiers["min_g_t4"] or min_tiers["min_u_t4"]:
    #   engine = "davinci"
    # elif min_tiers["min_g_t3"] or min_tiers["min_u_t3"]:
    #   engine = "curie"
    # else:
    engine = os.environ["OPENAIMODEL"]
    try:
      response = await self.bot.loop.run_in_executor(
          None,
          functools.partial(
              lambda: openai.Completion.create(
                  model=engine,
                  prompt=prompt,
                  temperature=0.8,
                  max_tokens=25 if not current_tier >= function_config.PremiumTiers.tier_1 else 50,
                  top_p=0.9,
                  user=str(author.id),
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

    if msg.author.bot:
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

    ctx = await self.bot.get_context(msg)
    if ctx.command is not None or msg.webhook_id is not None:
      return

    valid = validators.url(msg.clean_content)
    if valid or (hasattr(msg.channel, "type") and isinstance(msg.channel.type, (discord.TextChannel)) and msg.channel.type not in (discord.ChannelType.store, discord.ChannelType.voice, discord.ChannelType.category, discord.ChannelType.news)):
      return

    current_tier = function_config.PremiumTiers.free
    if msg.guild is not None:
      config = await self.get_guild_config(msg.guild.id)
      if config is None:
        self.bot.logger.error(f"Config was not available in chat for (guild: {msg.guild.id if msg.guild else None}) (channel type: {msg.channel.type if msg.channel else 'uhm'}) (user: {msg.author.id})")
        return

      chat_channel = config.chat_channel
      if chat_channel is not None and msg.channel != chat_channel:
        if msg.guild.me not in msg.mentions:
          return
      elif chat_channel is None and msg.guild.me not in msg.mentions:
          return

      current_tier = config.tier
    lang = config.lang if msg.guild is not None else "en"

    voted = await checks.user_voted(self.bot, msg.author)

    user_config = await self.get_user_patron_config(msg.author.id)
    if user_config is not None:
      current_tier = user_config.tier if user_config.tier > current_tier else current_tier

    if voted and not current_tier > function_config.PremiumTiers.voted:
      current_tier = function_config.PremiumTiers.voted

    if (len(msg.clean_content) > 100 and current_tier != function_config.PremiumTiers.free) or (len(msg.clean_content) > 200 and current_tier > function_config.PremiumTiers.free):
      return

    # Anything to do with sending messages needs to be below the above check
    response = None
    checker: SpamChecker = self._spam_check[msg.guild.id if msg.guild else msg.author.id]
    free: bool = checker.is_free_spam(msg)
    if checker.is_abs_min_spam(msg) or checker.is_abs_hour_spam(msg) or (free and not (voted and current_tier >= function_config.PremiumTiers.tier_1)) or (checker.is_voted_spam(msg) and (voted or current_tier >= function_config.PremiumTiers.tier_1)):
      advertise = True if free and not (voted and current_tier >= function_config.PremiumTiers.tier_1) else False
      retry_after = discord.utils.utcnow() + datetime.timedelta(seconds=checker.triggered(msg).get_retry_after())
      self.bot.logger.warning(f"Someone is being ratelimited at over {checker.get_triggered_rate(msg)} messages and can retry after <t:{int(retry_after.timestamp())}:R>")
      return await ctx.reply(embed=embed(title=f"You have sent me over `{checker.get_triggered_rate(msg)}` messages in that last `{checker.get_triggered_per(msg)} seconds` and are being rate limited, try again <t:{int(retry_after.timestamp())}:R>", description="If you would like to send me more messages you can get more by voting at https://top.gg/bot/476303446547365891/vote" if advertise else "", color=MessageColors.ERROR), mention_author=False)
    async with msg.channel.typing():
      translation = await Translation.from_text(msg.clean_content, from_lang=lang, parent=self)
      self.chat_history[msg.channel.id].insert(0, f"{ctx.author.display_name}: " + str(translation).strip('\n'))
      try:
        response = await self.openai_req(msg.channel, msg.author, msg.clean_content, current_tier)
      except openai.APIError:
        return await ctx.send(embed=embed(title="There was a problem connecting to OpenAI API, please try again later", color=MessageColors.ERROR))
      except openai.error.RateLimitError:
        return await ctx.send(embed=embed(title="Looks like the chatbot model hasn't finished loading, please try again in a few minutes.", color=MessageColors.ERROR))
      except openai.error.ServiceUnavailableError:
        return await ctx.send(embed=embed(title="Chatbot service is currently unavailable, please try again later.", color=MessageColors.ERROR))
    if response is not None:
      self.chat_history[msg.channel.id].insert(0, f"{msg.guild.me.display_name if msg.guild is not None else self.bot.user.display_name}:" + response)
      content_filter = await self.content_filter_check(response, str(msg.author.id))
    if translation is not None and translation.detectedSourceLanguage != "en" and response is not None and "dynamic" not in response:
      chars_to_strip = "?!,;'\":`"
      final_translation = await Translation.from_text(response.replace("dynamic", ""), from_lang="en", to_lang=translation.detectedSourceLanguage if translation.translatedText.strip(chars_to_strip).lower() != translation.input.strip(chars_to_strip).lower() else "en", parent=self)
      response = str(final_translation)

    if response is None or response == "":
      return
    if content_filter != 2:
      await ctx.reply(content=response if content_filter == 0 else f"{POSSIBLE_SENSITIVE_MESSAGE}{response}||", allowed_mentions=discord.AllowedMentions.none(), mention_author=False)
      await relay_info(f"{function_config.PremiumTiers.get_tier_name(current_tier)} - **{ctx.author.name}:** {ctx.message.clean_content}\n**Me:** {response}", self.bot, webhook=self.bot.log.log_chat)
    elif content_filter == 2:
      # if msg.type == discord.MessageType.thread_starter_message:
      #   await ctx.channel.send(content=POSSIBLE_OFFENSIVE_MESSAGE, mention_author=False)
      # else:
      await ctx.reply(content=POSSIBLE_OFFENSIVE_MESSAGE, mention_author=False)
      await relay_info(f"{function_config.PremiumTiers.get_tier_name(current_tier)} - **{ctx.author.name}:** {ctx.message.clean_content}\n**Me:** Possible offensive message: {response}", self.bot, webhook=self.bot.log.log_chat)

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


def setup(bot):
  bot.add_cog(Chat(bot))
