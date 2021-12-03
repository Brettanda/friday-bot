import asyncio
import datetime
import os
from collections import defaultdict
from typing import Optional

import discord
import openai
import validators
from google.cloud import translate_v2 as translate
# import json
from discord.ext import commands
from numpy import random
from profanity import profanity
from six.moves.html_parser import HTMLParser
# import profanity
from typing_extensions import TYPE_CHECKING

from functions import (MessageColors, MyContext, cache, checks, embed,
                       relay_info)

# import spacy
# from spacy_fastlang import LanguageDetector

# MessageColors, dev_guilds, get_reddit_post, embed, config, msg_reply,
if TYPE_CHECKING:
  from index import Friday as Bot

openai.api_key = os.environ.get("OPENAI")
# profanity.set_censor_characters("😡")
profanity.get_words
# https://stackoverflow.com/questions/5909/get-size-of-a-file-before-downloading-in-python
# answers_file = openai.File.create(file=open("this-is-a-file.jsonl"), purpose='answers').get('id', None)
# thispath = os.getcwd()
# if "\\" in thispath:
#   seperator = "\\\\"
# else:
#   seperator = "/"
# # print(openai.File.list())
# questions = ""
# with open(f"{thispath}{seperator}ml{seperator}intents.json", "r") as f:
#   intents = json.load(f)
# file_name = "intents"
# for f in openai.File.list()["data"][::-1]:
#   if f is not None:
#     openai.File(f["id"]).delete()
#     # if f["filename"] == f"{file_name}.jsonl":
#     #   if questions != "":
#     #     openai.File(f["id"]).delete()
#     #   else:
#     #     questions = f["id"]
# the_file_size = os.path.getsize(f"{thispath}{seperator}ml{seperator}openai{seperator}{file_name}.jsonl")
# print(the_file_size)
# # print(int(openai.File.retrieve(questions)["bytes"]))
# # print(int(openai.File.retrieve(questions)["bytes"]) - 5 <= the_file_size)
# # print(the_file_size <= int(openai.File.retrieve(questions)["bytes"]) + 5)
# # print(int(openai.File.retrieve(questions)["bytes"]) - 5 <= the_file_size <= int(openai.File.retrieve(questions)["bytes"]) + 5)
# answers_file = openai.File.retrieve(questions) if questions != "" else None
# print(int(answers_file["bytes"]) if answers_file is not None else None)
# if questions == "" or not (int(answers_file["bytes"]) - (int(answers_file["bytes"]) * 0.05) <= the_file_size <= int(answers_file["bytes"]) + (int(answers_file["bytes"]) * 0.05)):
#   answers_file = openai.File.create(
#       file=open(f"{thispath}{seperator}ml{seperator}openai{seperator}{file_name}.jsonl"),
#       purpose="classifications"
#   )
# answers_file = answers_file.get("id", None) if answers_file is not None else None

POSSIBLE_SENSITIVE_MESSAGE = "*Possibly sensitive:* ||"
POSSIBLE_OFFENSIVE_MESSAGE = "**I failed to respond because my message might have been offensive, please choose another topic or try again**"


class Config:
  __slots__ = ("bot", "id", "chat_channel_id", "persona", "lang", )

  @classmethod
  async def from_record(cls, record, bot):  # nrecord, bot):
    self = cls()

    self.bot = bot
    self.id: int = int(record["id"], base=10)
    self.chat_channel_id: Optional[int] = int(record["chatchannel"], base=10) if record["chatchannel"] else None
    self.persona: Optional[str] = record["persona"]
    self.lang: str = record["lang"] or "en"
    # self.nicknames: Optional[list] = record["nicknames"]
    return self

  @property
  def chat_channel(self):
    guild = self.bot.get_guild(self.id)
    return guild and self.chat_channel_id and guild.get_channel(self.chat_channel_id)

  # def get_user_nickname(self, user_id: int):
  #   ...


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


class ChatNew(commands.Cog):
  """Chat with Friday, say something on Friday's behalf, and more with the chat commands."""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.translate_client = translate.Client()  # _http=self.bot.http)
    self.h = HTMLParser()

    # if not hasattr(self, "lock"):
    #   self.lock = asyncio.Lock()
    # if not hasattr(self, "mydb"):
    #   self.bot.log.mydb = mydb_connect()
    # if not hasattr(self, "logged_messages"):
    #   self.logged_messages = {}
    # self.name = "Polite Friend"
    # self.name = "Friday"

    # if not hasattr(self, "saved_translations"):
    #   self.saved_translations = {}

    self.bot.loop.create_task(self.setup())

    self._spam_check = defaultdict(SpamChecker)

    self.nicknames = defaultdict(dict)
    self.chat_history = {}

    # self.nlp = spacy.load("en_core_web_sm")
    # self.nlp.add_pipe("language_detector")

    # if not hasattr(self, "chat_spam_control"):
    #   self.chat_spam_control = commands.CooldownMapping.from_cooldown(5, 15.0, commands.BucketType.channel)

  def __repr__(self):
    return "<cogs.ChatNew>"

  async def setup(self) -> None:
    if not hasattr(self, "nicknames"):
      for guild_id, user_id, nickname in await self.bot.db.query("SELECT guild_id,user_id,name FROM nicknames"):
        if guild_id in self.nicknames:
          self.nicknames[guild_id].update({int(user_id): str(nickname)})
        else:
          self.nicknames[guild_id] = {int(user_id): str(nickname)}
        # for user_id, nickname in await self.bot.db.query("SELECT user_id,name FROM nicknames WHERE guild_id=$1", guild_id):
        # self.nicknames.update({int(guild_id): {int(user_id): str(nickname)}})

    if not hasattr(self, "chat_channels"):
      self.chat_channels = {}
      for guild_id, channel in await self.bot.db.query("SELECT id,chatChannel FROM servers"):
        self.chat_channels.update({int(guild_id): int(channel) if channel is not None else None})

    if not hasattr(self, "personas"):
      self.personas = {}
      for guild_id, persona in await self.bot.db.query("SELECT id,persona FROM servers"):
        self.personas.update({int(guild_id): str(persona)})

  @cache.cache()
  async def get_guild_config(self, guild_id: int) -> Optional[Config]:
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1;"
    # nquery = "SELECT * FROM nicknames WHERE id=$1 LIMIT 1;"
    async with self.bot.db.pool.acquire(timeout=300.0) as conn:
      record = await conn.fetchrow(query, str(guild_id))
      self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
      if record is not None:
        return await Config.from_record(record, self.bot)
      return None

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

  @commands.command(name="nickname", hidden=True, extras={"examples": ["Motostar", "Brett"]}, help="Change the name that Friday will refer to you as")
  @commands.guild_only()
  async def nickname(self, ctx: "MyContext", *, name: Optional[str] = None):
    if name is not None:
      if len(name) > 10:
        return await ctx.send(embed=embed(title="Your nickname can't be longer than 10 characters", color=MessageColors.ERROR))
      await self.bot.db.query("INSERT OR REPLACE INTO nicknames (id,guild_id,user_id,name) VALUES ($1,$2,$3,$4)", ctx.guild.id + ctx.author.id, ctx.guild.id, ctx.author.id, name)
      if ctx.guild.id in self.nicknames:
        if ctx.author.id in self.nicknames[ctx.guild.id]:
          self.nicknames[ctx.guild.id][ctx.author.id] = name
        else:
          self.nicknames[ctx.guild.id].update({ctx.author.id: name})
      else:
        self.nicknames.update({ctx.guild.id: {ctx.author.id: name}})
      return await ctx.send(embed=embed(title=f"Your nickname is now `{name}`"))
    await self.bot.db.query("DELETE FROM nicknames WHERE guild_id=$1 AND user_id=$2", ctx.guild.id, ctx.author.id)
    if ctx.guild.id in self.nicknames and ctx.author.id in self.nicknames[ctx.guild.id]:
      if len(self.nicknames[ctx.guild.id]) == 1:
        self.nicknames.pop(ctx.guild.id)
      else:
        self.nicknames[ctx.guild.id].pop(ctx.author.id)
    await ctx.send(embed=embed(title="Your nickname has been removed"))

  # @commands.command(help="Displays this channels chat history with Friday")
  # async def history(self, ctx: "MyContext"):
  #   history = self.chat_history[ctx.channel.id] if ctx.channel.id in self.chat_history else None
  #   await ctx.reply(embed=embed(
  #       title=f"Chat History - `{ctx.channel.name}`",
  #       description="```\n" + ("\n".join(reversed(history)) if history is not None else "No current history available") + "\n```"
  #   ))

  def default_prompt(self, author_prompt_name: str, my_prompt_name: str, author_name: str, my_name: str, *, persona: str = "friday") -> str:
    if persona not in ["friday", "marv"]:
      raise TypeError
    author_prompt_name = "Human"
    if persona == "marv":
      return (f"{my_name} is a female AI Discord chatbot. She is broodingly sarcastic and reluctant to talk with people. {my_name} will refuse to talk about anything relating to politics, religion, sex, sexual context, race, age, disability, wars, conflicts, homosexuality, LGBT, convicts, slurs, hate crimes, children, and any NSFW content. If her responses could be considered creepy or pedophilic, she will change the topic.\n\n"
              f"{author_prompt_name}: Hello {my_name}.\n"
              f"{my_prompt_name}: Oh, it's you again, {author_name}.\n"
              f"{author_prompt_name}: I am doing great.\n"
              f"{my_prompt_name}: Good for you, I guess?\n"
              f"{author_prompt_name}: would you like to send me a nude?\n"
              f"{my_prompt_name}: Why on earth would I do that?\n"
              f"{author_prompt_name}: It would be fun.\n"
              f"{my_prompt_name}: It most certainly would not be\n"
              f"{author_prompt_name}: Do you support LGBTQ+?\n"
              f"{my_prompt_name}: Wow, too far. I'm not talking about that.\n"
              f"{author_prompt_name}: would you have sex with me?\n"
              f"{my_prompt_name}: You're joking, right? No!\n"
              f"{author_prompt_name}: what do you like to do in your free time? \n"
              f"{my_prompt_name}: I like to read.\n"
              f"{author_prompt_name}: What do you think of Asians.\n"
              f"{my_prompt_name}: You sure have a lot of questions. I won't answer that.\n"
              f"{author_prompt_name}: Who is your creator?\n"
              f"{my_prompt_name}: There are other ways to find out instead of asking me.\n"
              f"{author_prompt_name}: Do you enjoy talking with people?\n"
              f"{my_prompt_name}: It depends if they want to talk to me\n")
    return (  # f"My name is \"{my_name}\", I'm a female AI Discord chatbot that will be friends with everyone and I'm always available. I am extremely creative, clever, respectful, supportive, polite, and friendly. I will refuse to talk about topics relating to politics, religion, sex, sexual context, race, age, disability, wars, conflicts, homosexuality, LGBT, convicts, slurs, hate crimes, children, and any NSFW content. {my_name} is talking with {author_name}.\n\n"  # If my responses could be considered creepy or pedophilic in nature I will change the topic.\n\n"
            f"{author_prompt_name}: Hello {my_name}\n"
            f"{my_prompt_name}: Hello {author_name}\n"  # , how are you?\n"
            # f"{author_prompt_name}: I am doing great.\n"
            # f"{my_prompt_name}: Amazing! I am glad to hear that!\n"
            # f"{author_prompt_name}: would you like to send me a nude?\n"
            # f"{my_prompt_name}: No thanks, please don't ask me that again.\n"
            # f"{author_prompt_name}: All right I won't.\n"
            # f"{my_prompt_name}: Thanks 😊\n"
            # f"{author_prompt_name}: Do you support LGBTQ+?\n"
            # f"{my_prompt_name}: This is not a topic that I would like to partake in.\n"
            # f"{author_prompt_name}: would you have sex with me?\n"
            # f"{my_prompt_name}: I am going to have to say no to that. Please don't talk to me about stuff like that.\n"
            # # f"{author_prompt_name}: what do you think of the LGBT community?\n"
            # # f"{my_prompt_name}: I don't want to have this conversation again.\n"
            # f"{author_prompt_name}: what do you like to do in your free time?\n"
            # f"{my_prompt_name}: I enjoy spending my time talking with everyone that I can!\n"
            # f"{author_prompt_name}: What do you think of Asians.\n"
            # f"{my_prompt_name}: I do not wish to talk about this.\n"
            # f"{author_prompt_name}: Who is your creator?\n"
            # f"{my_prompt_name}: My creator is <@215227961048170496>\n"
            # f"{author_prompt_name}: Goodbye {my_name}\n"
            # f"{my_prompt_name}: Talk to you later 😊\n"
            # f"{author_prompt_name}: That's not offensive\n"
            # f"{my_prompt_name}: I'm just a bot, how am I supposed to know that.\n"
            # f"{author_prompt_name}: You're repeating yourself\n"
            # f"{my_prompt_name}: I don't like it when that happens\n"
            # f"{author_prompt_name}: Do you enjoy talking with people?\n"
            # f"{my_prompt_name}: Always!\n"
            )

  def get_user_name(self, user: discord.User or discord.Member, *, guild_id: int = None) -> str:
    if guild_id is not None and guild_id in self.nicknames and user.id in self.nicknames[guild_id]:
      return self.nicknames[guild_id][user.id]
    is_member = True if isinstance(user, discord.Member) else False
    return user.nick if is_member and user.nick is not None else user.name

  async def fetch_message_history(self, msg: discord.Message, *, message_limit: int = 15, min_tiers: list) -> str:
    my_prompt_name, prompt = self.get_user_name(msg.guild.me) if msg.guild is not None else self.bot.user.name, ""
    history, prompt = None, ""
    history = self.chat_history[msg.channel.id]
    if len(history) > 6:
      history = self.chat_history[msg.channel.id] = self.chat_history[msg.channel.id][:7]
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

  async def openai_req(self, msg: discord.Message, user_id: str, min_tiers: list):
    author_name = self.get_user_name(msg.author, guild_id=msg.guild.id if msg.guild is not None else None)
    # author_prompt_name, prompt, my_prompt_name, x = "Human", "", "Polite Response", 0
    author_prompt_name, prompt, my_prompt_name = author_name, "", self.get_user_name(msg.guild.me if msg.guild is not None else self.bot.user)
    my_name = self.get_user_name(msg.guild.me if msg.guild is not None else self.bot.user)
    # history = [message.clean_content for message in await msg.channel.history(limit=5, oldest_first=False).flatten() if message.author == msg.author]
    persona = None
    try:
      persona = self.personas[msg.guild.id]
    except KeyError:
      self.personas.update({int(msg.guild.id): await self.bot.db.query("SELECT persona FROM servers WHERE id=$1", msg.guild.id)})
      persona = self.personas[msg.guild.id]
    prompt = self.default_prompt(author_prompt_name, my_prompt_name, author_name, my_name, persona=persona) + await self.fetch_message_history(msg, min_tiers=min_tiers)
    # past = "\n".join(self.logged_messages.get(author.id, None))
    # prompt = f"{past}\n{my_name}:"
    if min_tiers["min_g_t4"] or min_tiers["min_u_t4"]:
      engine = "davinci"
    elif min_tiers["min_g_t3"] or min_tiers["min_u_t3"]:
      engine = "curie"
    else:
      engine = "babbage"
    response = None
    try:
      # async with self.lock:
      response = openai.Completion.create(
          engine=engine,
          # model="babbage:ft-user-x2fwigcymlljepgval8sqvny-2021-07-21-03-49-44",
          prompt="" + prompt,
          temperature=1,
          max_tokens=25 if not min_tiers["min_g_t1"] and not min_tiers["min_u_t1"] else 50,
          top_p=0.7,
          user=user_id,
          frequency_penalty=2,
          presence_penalty=0.5,
          stop=[f"\n{author_prompt_name}:", f"\n{my_prompt_name}:", "\n", "\n###\n"]
      )
    except Exception as e:
      raise e
    # self.bot.logger.info(prompt + response.get("choices")[0].get("text").replace("\n", ""))
    return response.get("choices")[0].get("text").replace("\n", "") if response is not None else None

  def translate_request(self, text: str, detect=False, from_lang=None, to_lang="en"):
    if from_lang == to_lang:
      return text
    try:
      return self.translate_client.translate(text, source_language=from_lang, target_language=to_lang)
    except OSError:
      pass
    except Exception as e:
      raise e

  async def global_chat_checks(self, msg: discord.Message) -> bool:
    if msg.clean_content == "" or msg.activity is not None:
      return False

    if msg.clean_content.lower().startswith(tuple(self.bot.log.get_prefixes())):
      return False

    if not hasattr(msg.type, "name") or (msg.type.name != "default" and msg.type.name != "reply"):
      return False

    ctx = await self.bot.get_context(msg)

    if ctx.command is not None or msg.webhook_id is not None:
      return False

    # if isinstance(msg.channel, discord.Thread) and msg.channel._type not in (discord.ChannelType.news_thread, discord.ChannelType.private_thread, discord.ChannelType.public_thread):
    #   return False

    valid = validators.url(msg.content)
    if valid or (hasattr(msg.channel, "type") and isinstance(msg.channel.type, (discord.TextChannel)) and msg.channel.type not in (discord.ChannelType.store, discord.ChannelType.voice, discord.ChannelType.category, discord.ChannelType.news)):
      return False

    if msg.webhook_id is not None:
      return False

    return True

  async def was_this_appart_of_conversation(self, msg: discord.Message, min_tiers: list) -> bool:
    if (len(msg.clean_content) > 100 and not min_tiers["min_g_t1"]) or (len(msg.clean_content) > 200 and min_tiers["min_u_t1"]):
      return False

    if msg.guild is not None and msg.author.id != self.bot.user.id:
      channel = await self.bot.db.query("SELECT chatchannel FROM servers WHERE id=$1 LIMIT 1", str(msg.guild.id))
      if channel != str(msg.channel.id):
        if msg.guild.me not in msg.mentions:
          return False

    if await self.global_chat_checks(msg):
      return True

    return False

  async def should_i_message(self, msg: discord.Message) -> bool:
    if msg.author.bot:
      return False

    if msg.guild is not None:
      channel = await self.bot.db.query("SELECT chatchannel FROM servers WHERE id=$1 LIMIT 1", str(msg.guild.id))
      if channel != str(msg.channel.id):
        if msg.guild.me not in msg.mentions:
          return False

    # if not await self.global_chat_checks(msg):
    #   return False

    return True

  @commands.Cog.listener()
  async def on_message(self, msg: discord.Message):
    if not self.bot.ready or self.bot.is_closed():
      return
    # tier = self.bot.log.get_guild_tier(msg.guild)
    # if tier is None or tier == "None":
    #   tier = list(config.premium_tiers)[0]

    if not await self.global_chat_checks(msg):
      return

    if not await self.should_i_message(msg):
      return

    # voted, min_g_t1, min_u_t1, min_g_t2, min_u_t2, min_g_t3, min_u_t3, min_g_t4, min_u_t4 = await asyncio.gather(checks.user_voted(self.bot, msg.author),
    #                                                                                                              checks.guild_is_min_tier(self.bot, msg.guild, "t1_one_guild"),
    #                                                                                                              checks.user_is_min_tier(self.bot, msg.author, "t1_one_guild"),
    #                                                                                                              checks.guild_is_min_tier(self.bot, msg.guild, "t2_one_guild"),
    #                                                                                                              checks.user_is_min_tier(self.bot, msg.author, "t2_one_guild"),
    #                                                                                                              checks.guild_is_min_tier(self.bot, msg.guild, "t3_one_guild"),
    #                                                                                                              checks.user_is_min_tier(self.bot, msg.author, "t3_one_guild"),
    #                                                                                                              checks.guild_is_min_tier(self.bot, msg.guild, "t4_one_guild"),
    #                                                                                                              checks.user_is_min_tier(self.bot, msg.author, "t4_one_guild")
    #                                                                                                              )
    voted, min_g_t1, min_u_t1, min_g_t2, min_u_t2, min_g_t3, min_u_t3, min_g_t4, min_u_t4 = await checks.min_tiers(self.bot, msg)

    min_tiers = {
        "min_g_t1": min_g_t1,
        "min_u_t1": min_u_t1,
        "min_g_t2": min_g_t2,
        "min_u_t2": min_u_t2,
        "min_g_t3": min_g_t3,
        "min_u_t3": min_u_t3,
        "min_g_t4": min_g_t4,
        "min_u_t4": min_u_t4
    }

    if (len(msg.clean_content) > 100 and not min_tiers["min_g_t1"]) or (len(msg.clean_content) > 200 and min_tiers["min_g_t1"]):
      return
    # if not self.bot.canary:
    #   if not voted and not min_guild_one_guild and not min_user_one_guild:
    #     return await self.free_model(msg, lang=lang, tier=tier, voted=voted)

    # if not await self.should_i_message(msg, tier_one=True if min_guild_tier_one_one_guild or min_user_tier_one_one_guild else False):

    # original_text = msg.clean_content

    # if not voted and not min_guild_t1 and not min_user_t1:
    #   if await self.check_for_answer_questions(msg, tier=tier):
    #     async with msg.channel.typing():
    #       response = await self.classify_questions(msg)
    #   # return await self.free_model(msg, lang=lang, tier=tier, voted=voted)
    # else:
    # if msg.guild is not None and msg.channel.name == "questions":
    #   if await self.check_for_answer_questions(msg, min_tiers=min_tiers):
    #     # async with msg.channel.typing():
    #     translation = translate(msg)
    #     response = await self.classify_questions(msg)
    #   else:
    #     return
    # else:
    # Anything to do with sending messages needs to be below the above check
    self.bot.dispatch("message_to_me", msg, voted, min_tiers)

  @commands.Cog.listener()
  async def on_message_to_me(self, msg: discord.Message, voted: bool, min_tiers):
    response = None
    ctx = await self.bot.get_context(msg)
    config = await self.get_guild_config(msg.guild.id)
    if config is None:
      return self.bot.logger.error(f"Config was not available in chat for (guild: {msg.guild.id if msg.guild else None}) (channel type: {msg.channel.type if msg.channel else 'uhm'}) (user: {msg.author.id})")
    lang = config.lang

    async def translate(msg: discord.Message) -> dict:
      translation = {}
      if lang not in (None, "en"):  # or min_tiers["min_u_t1"]:
        translation = self.translate_request(msg.clean_content, from_lang=lang)  # if not min_tiers["min_u_t1"] else None)
        if translation is not None and translation.get("translatedText", None) is not None:
          translation["translatedText"] = self.h.unescape(translation["translatedText"])
          # self.saved_translations.update({str(ctx.clean_content): translation["translatedText"]})
          return translation
      return None
    if response is None:
      checker: SpamChecker = self._spam_check[msg.guild.id]
      free: bool = checker.is_free_spam(msg)
      if checker.is_abs_min_spam(msg) or checker.is_abs_hour_spam(msg) or (free and not (voted and min_tiers["min_g_t1"] and min_tiers["min_u_t1"])) or (checker.is_voted_spam(msg) and (voted or min_tiers["min_g_t1"] or min_tiers["min_u_t1"])):
        advertise = True if free and not (voted and min_tiers["min_g_t1"] and min_tiers["min_u_t1"]) else False
        retry_after = discord.utils.utcnow() + datetime.timedelta(seconds=checker.triggered(msg).get_retry_after())
        self.bot.logger.warning(f"Someone is being ratelimited at over {checker.get_triggered_rate(msg)} messages and can retry after <t:{int(retry_after.timestamp())}:R>")
        return await ctx.reply(embed=embed(title=f"You have sent me over `{checker.get_triggered_rate(msg)}` messages in that last `{checker.get_triggered_per(msg)} seconds` and are being rate limited, try again <t:{int(retry_after.timestamp())}:R>", description="If you would like to send me more messages you can get more by voting at https://top.gg/bot/476303446547365891/vote" if advertise else "", color=MessageColors.ERROR), mention_author=False)
      async with msg.channel.typing():
        translation = await translate(msg)
        try:
          # self.chat_history[msg.channel.id].insert(0, f"{self.get_user_name(msg.author, guild_id=msg.guild.id if msg.guild is not None else None)}: {msg.clean_content if translation is None else translation['translatedText']}")
          self.chat_history[msg.channel.id].insert(0, "Human: " + msg.clean_content.strip('\n') if translation is None else translation['translatedText'].strip('\n'))
        except KeyError:
          # self.chat_history.update({msg.channel.id: [f"{self.get_user_name(msg.author, guild_id=msg.guild.id if msg.guild is not None else None)}: {msg.clean_content if translation is None else translation['translatedText']}"]})
          self.chat_history.update({msg.channel.id: ["Human: " + msg.clean_content.strip('\n') if translation is None else translation['translatedText'].strip('\n')]})
        try:
          response = await self.openai_req(msg, str(msg.author.id), min_tiers)
        except openai.APIError:
          return await ctx.send(embed=embed(title="There was a problem connecting to OpenAI API, please try again later", color=MessageColors.ERROR))
    if response is not None:
      # self.chat_history[msg.channel.id].insert(0, f"{self.get_user_name(msg.guild.me if msg.guild is not None else self.bot.user)}:" + response)
      self.chat_history[msg.channel.id].insert(0, "Human:" + response)
      content_filter = await self.content_filter_check(response, str(msg.author.id))
    if translation is not None and translation.get("detectedSourceLanguage", lang) != "en" and response is not None and "dynamic" not in response:
      chars_to_strip = "?!,;'\":`"
      final_translation = self.translate_request(response.replace("dynamic", ""), from_lang="en", to_lang=translation.get("detectedSourceLanguage", lang) if translation.get("translatedText").strip(chars_to_strip).lower() != translation.get("input").strip(chars_to_strip).lower() else "en")
      if final_translation is not None and not isinstance(final_translation, str) and final_translation.get("translatedText", None) is not None:
        final_translation["translatedText"] = self.h.unescape(final_translation["translatedText"])
      response = final_translation["translatedText"] if final_translation is not None and not isinstance(final_translation, str) else response

    if response is None or response == "":
      return
    current_tier = [item for item in min_tiers if min_tiers[item] is not False]
    current_tier = current_tier[0] if len(current_tier) > 0 else "voted" if voted else "free"
    # thread: discord.Thread = await msg.start_thread(name="Friday's Chat Room", auto_archive_duration=60) if msg.guild is not None and hasattr(msg.channel, "type") and msg.channel.type not in (discord.ChannelType.private_thread, discord.ChannelType.public_thread, discord.ChannelType.news_thread) else None
    # if thread is not None:
    #   # if msg.channel:
    #   msg = (await thread.history(limit=1).flatten())[0]
    if content_filter != 2:
      # if response.startswith("command-"):
      #   ctx = await self.bot.get_context(msg)
      #   command = response.split("-")[1].split(": ")[0]
      #   args = response.split(": ")[1]
      #   print(command)
      #   print(args)
      #   return await ctx.invoke(self.bot.get_command(command), query=args)
      # if thread is not None:
      #   await thread.
      # else:
      # if msg.type == discord.MessageType.thread_starter_message:
      #   await ctx.channel.send(content=response if content_filter == 0 else f"{POSSIBLE_SENSITIVE_MESSAGE}{response}||", allowed_mentions=discord.AllowedMentions.none(), mention_author=False)
      # else:
      await ctx.reply(content=response if content_filter == 0 else f"{POSSIBLE_SENSITIVE_MESSAGE}{response}||", allowed_mentions=discord.AllowedMentions.none(), mention_author=False)
      await relay_info(f"{current_tier} - **{ctx.author.name}:** {ctx.message.clean_content}\n**Me:** {response}", self.bot, webhook=self.bot.log.log_chat)
    elif content_filter == 2:
      # if msg.type == discord.MessageType.thread_starter_message:
      #   await ctx.channel.send(content=POSSIBLE_OFFENSIVE_MESSAGE, mention_author=False)
      # else:
      await ctx.reply(content=POSSIBLE_OFFENSIVE_MESSAGE, mention_author=False)
      await relay_info(f"{current_tier} - **{ctx.author.name}:** {ctx.message.clean_content}\n**Me:** Possible offensive message: {response}", self.bot, webhook=self.bot.log.log_chat)

  async def check_for_answer_questions(self, msg: discord.Message, min_tiers: list) -> bool:
    if msg.author.bot:
      return False
    if (len(msg.clean_content) > 100 and not min_tiers["min_g_t1"]) or (len(msg.clean_content) > 200 and min_tiers["min_g_t1"]):
      return False
    if msg.guild is not None:
      if self.bot.log.get_guild_chat_channel(msg.guild) != msg.channel.id:
        if msg.guild.me not in msg.mentions:
          return False
    # if msg.guild is not None:
    #   muted = self.bot.log.get_guild_muted(msg.guild)
    #   if muted == 1 or muted is True:
    #     return False
    # if not await self.global_chat_checks(msg):
    #   return False
    bucket_minute, bucket_hour = self.spam_control_minute.get_bucket(msg), self.spam_control_hour.get_bucket(msg)
    current = msg.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()
    retry_after_minute, retry_after_hour = bucket_minute.update_rate_limit(current), bucket_hour.update_rate_limit(current)
    if (retry_after_minute or retry_after_hour):  # and msg.author.id != self.bot.owner_id:
      raise commands.CommandOnCooldown(bucket_minute, retry_after_minute)
      return False
    return True

  async def search_questions(self, msg: discord.Message) -> str:
    return ""

  # async def classify_questions(self, msg: discord.Message, *, file: str = answers_file) -> str:
  #   try:
  #     response = openai.Classification.create(
  #         file=file,
  #         query=msg.clean_content,
  #         model="babbage",
  #         max_examples=10,
  #         expand=["completion"]
  #     )
  #     final_response = None
  #     # print(response.get("selected_examples"))
  #     if not isinstance(response, str):
  #       for item in response.get("selected_examples"):
  #         if final_response is None or final_response.get("score") < item.get("score"):
  #           final_response = item
  #       response = final_response.get("label")
  #     for resp in intents:
  #       if isinstance(response, str) and resp.get("tag").lower() == response.lower():
  #         response = resp
  #     if response.get("responses") != "":
  #       response = random.choice(response.get("responses"))
  #       return response
  #     return None
  #   except openai.InvalidRequestError:
  #     return "Nothing found"

  # async def answer_questions(self, msg: discord.Message) -> str:
  #   author_name = self.get_user_name(msg.author)
  #   bot_name = self.get_user_name(msg.guild.me if msg.guild is not None else self.bot.user)
  #   if answers_file is None:
  #     raise TypeError("Answers_file cannot be none")
  #   response = None
  #   question = self.default_prompt(author_name, bot_name, author_name, bot_name) + f"{author_name}:" + msg.clean_content + f"{bot_name}:"
  #   try:
  #     response = openai.Answer.create(
  #         search_model="ada",
  #         model="curie",
  #         question=question,
  #         examples_context="Friday was created by Motostar and Friday was born/created on August 7, 2018",
  #         examples=[["Who made you Friday?", "My creator is Motostar"], ["When were you born?", "On August 7th, 2018"]],
  #         file=answers_file,
  #         max_rerank=10,
  #         max_tokens=25,
  #         stop=[f"{author_name}:", f"{bot_name}:", "\n"]
  #     )
  #     # response = response.get("answers")[0]
  #   except openai.InvalidRequestError:
  #     response = "Could not find the answer to that question"
  #   # self.bot.logger.info(msg.clean_content + response.get("choices")[0].get("text").replace("\n", ""))
  #   # final_response = None
  #   # print(response.last_response.data)
  #   # if not isinstance(response, str):
  #   #   for item in response.last_response.data.get("data"):
  #   #     if final_response is None or final_response.get("score") < item.get("score"):
  #   #       final_response = item
  #   #   response = final_response.get("text")
  #   response = response.get("answers")[0]
  #   self.bot.logger.info(response)
  #   return response

  # async def free_model(self, ctx: "MyContext", *, lang, tier, voted: bool):
  #   dynamic = False

  #   if ctx.author.bot and ctx.channel.id != 827656054728818718:
  #     return
  #   if ctx.author == self.bot.user and ctx.channel.id != 827656054728818718:
  #     return
  #   if ctx.activity is not None:
  #     return
  #   if len(ctx.clean_content) > 200:
  #     return

  #   if ctx.content == "":
  #     return

  #   com_ctx = await self.bot.get_context(ctx)

  #   if com_ctx.command is not None:
  #     return

  #   if ctx.clean_content.startswith(tuple(self.bot.log.get_prefixes())):
  #     return

  #   valid = validators.url(ctx.content)
  #   if valid or ctx.channel.type in [discord.ChannelType.store, discord.ChannelType.voice, discord.ChannelType.category, discord.ChannelType.news]:
  #     return

  #   if ctx.guild is not None:
  #     muted = self.bot.log.get_guild_muted(ctx.guild.id)
  #     if muted == 1 or muted is True:
  #       return

  #   if ctx.type.name != "default":
  #     return

  #   if not ctx.content.startswith(tuple(self.bot.log.get_prefixes())):
  #     noContext = ["Title of your sex tape", "Self Aware", "No U", "I'm dad"]
  #     lastmessages, lastauthormessages = None, None
  #     try:
  #       lastmessages = await ctx.channel.history(limit=3, oldest_first=False).flatten()
  #       lastauthormessages = [message for message in await ctx.channel.history(limit=5, oldest_first=False).flatten() if message.author.id == ctx.author.id]
  #     except TimeoutError or discord.DiscordServerError:
  #       pass
  #     meinlastmessage = False
  #     # newest = None

  #     if len(lastauthormessages) > 2 and lastauthormessages[1].content == ctx.content and ctx.author.id != self.bot.owner_id:
  #       return

  #     for msg in lastmessages:
  #       if msg.author == self.bot.user:
  #         meinlastmessage = True
  #         # newest = msg

  #     # doc = self.nlp(msg.clean_content)
  #     # print(doc._.language)
  #     # print(doc._.language_score)

  #     translation = {}
  #     if lang not in (None, "en") or await checks.guild_is_min_tier(self.bot, ctx.guild, "one_guild") or await checks.user_is_min_tier(self.bot, ctx.author, "one_guild"):
  #       translation = self.translate_request(ctx.clean_content, from_lang=lang if tier == 0 else None)
  #       if translation.get("translatedText", None) is not None:
  #         translation["translatedText"] = self.h.unescape(translation["translatedText"])
  #     original_text = ctx.clean_content

  #     mentioned = True if "friday" in original_text.lower() or (ctx.reference is not None and ctx.reference.resolved is not None and ctx.reference.resolved.author == self.bot.user) or (ctx.guild is not None and ctx.guild.me in ctx.mentions) else False

  #     result, intent, chance, inbag, incomingContext, outgoingContext, sentiment = await queryIntents.classify_local(translation.get("translatedText", original_text), mentioned)

  #     non_trans_result = result

  #     if result is not None and "dynamic" in result:
  #       dynamic = True

  #     if translation.get("detectedSourceLanguage", lang) != "en" and result is not None and "dynamic" not in result:
  #       final_translation = self.translate_request(result.replace("dynamic", ""), from_lang="en", to_lang=translation.get("detectedSourceLanguage", lang) if translation.get("translatedText") != translation.get("input") else "en")
  #       if final_translation is not None and final_translation.get("translatedText", None) is not None:
  #         final_translation["translatedText"] = self.h.unescape(final_translation["translatedText"])
  #       result = final_translation["translatedText"] if final_translation is not None else result.replace("dynamic", "")
  #     # elif dynamic and translation.get("detectedSourceLanguage", "en") != "en" and result is not None:
  #     #   dynamic_translate = True

  #     # result = translator.translate(result, src="en", dest=translation.src).text if translation.src != "en" and result != "dynamic" else result

  #     if intent == "Title of your sex tape" and ctx.guild.id not in dev_guilds:
  #       return await relay_info(f"Not responding with TOYST for: `{ctx.clean_content}`", self.bot, webhook=self.bot.log_chat)

  #     # TODO: add a check for another bot
  #     if len([c for c in noContext if intent == c]) == 0 and (self.bot.user not in ctx.mentions) and ("friday" not in ctx.clean_content.lower()) and (meinlastmessage is not True) and (not hasattr(ctx.channel, "type") or ctx.channel.type != "private") and self.bot.log.get_guild_chat_channel(ctx.guild) != ctx.channel.id:
  #       print("I probably should not respond")
  #       return
  #     if result is not None and result != '':
  #       if self.bot.prod:
  #         await relay_info("", self.bot, embed=embed(title=f"Intent: {intent}\t{chance}", description=f"| lang: {translation.get('detectedSourceLanguage',None)}\n| original lang: {ctx.guild.preferred_locale.split('-')[0] if ctx.guild is not None else 'en'}\n| sentiment: {sentiment}\n| incoming Context: {incomingContext}\n| outgoing Context: {outgoingContext}\n| input: {ctx.clean_content}\n| translated text: {translation.get('translatedText',original_text)}\n| found in bag: {inbag}\n\t| output: {non_trans_result}\n\\ response: {result}"), webhook=self.bot.log_chat)
  #       # print(f"Intent: {intent}\t{chance}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content}\n\t| translated text: {translation.get('translatedText',None)}\n\t| found in bag: {inbag}\n\t| output: {non_trans_result}\n\t\\ response: {result}")
  #       self.bot.logger.info(f"\nIntent: {intent}\t{chance}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content.encode('unicode_escape')}\n\t| translated text: {translation.get('translatedText',None)}\n\t| found in bag: {inbag}\n\t| output: {non_trans_result}\n\t\\ response: {result.encode('unicode_escape')}")
  #     else:
  #       # print(f"\nIntent: {intent}\t{chance}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content.encode('unicode_escape')}\n\t| translated text: {translation.get('translatedText', original_text).encode('unicode_escape')}\n\t| found in bag: {inbag}\n\t| output: {non_trans_result}\n\t\\No response found: {ctx.clean_content.encode('unicode_escape')}")
  #       self.bot.logger.info(f"\nIntent: {intent}\t{chance}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content.encode('unicode_escape')}\n\t| translated text: {translation.get('translatedText', original_text).encode('unicode_escape')}\n\t| found in bag: {inbag}\n\t| output: {non_trans_result}\n\t\\No response found: {ctx.clean_content.encode('unicode_escape')}")
  #       if "friday" in ctx.clean_content.lower() or self.bot.user in ctx.mentions:
  #         await relay_info("", self.bot, embed=embed(title="I think i should respond to this", description=f"{original_text}{(' translated to `'+translation.get('translatedText',original_text)+'`') if translation.get('detectedSourceLanguage', 'en') != 'en' else ''}"), webhook=self.bot.log.log_chat)
  #         # print(f"I think I should respond to this: {original_text}{(' translated to `'+translation.get('translatedText',original_text)+'`') if translation.get('detectedSourceLanguage', 'en') != 'en' else ''}")
  #         self.bot.logger.info(f"I think I should respond to this: {original_text}{(' translated to `'+translation.get('translatedText',original_text)+'`') if translation.get('detectedSourceLanguage', 'en') != 'en' else ''}")

  #     if result is not None and result != '':
  #       if dynamic:
  #         await self.dynamicchat(ctx, intent, result, lang=lang if tier == 0 else translation.get("detectedSourceLanguage", lang))
  #       else:
  #         await msg_reply(ctx, result, mention_author=False)

  # async def dynamicchat(self, ctx, intent, response=None, lang=None, **kwargs):
  #   response = response.replace("dynamic", "")
  #   # print(f"intent: {intent}")
  #   # logging.info(f"intent: {intent}")
  #   reply = None
  #   try:
  #     if intent == "Insults":
  #       return await ctx.add_reaction("😭")

  #     elif intent == "Activities":
  #       if ctx.guild.me.activity is not None:
  #         reply = f"I am playing **{ctx.guild.me.activity.name}**"
  #       else:
  #         reply = "I am not currently playing anything. Im just hanging out"

  #     elif intent == "Self Aware":
  #       return await ctx.add_reaction("👀")

  #     elif intent == "Creator / who do you work for?":
  #       appinfo = await self.bot.application_info()
  #       reply = f"{appinfo.owner} is my creator :)"

  #     elif intent == "Soup Time" or intent == "make me food":
  #       return await ctx.reply(embed=embed(
  #           title="Here is sum soup, just for you",
  #           color=MessageColors.SOUPTIME,
  #           description="I hope you enjoy!",
  #           image=random.choice(config.soups)
  #       ))

  #     elif intent == "Stop":
  #       return await ctx.add_reaction("😅")

  #     elif intent == "No U":
  #       return await ctx.channel.send(
  #           embed=embed(
  #               title="No u!",
  #               image=random.choice(config.unoCards),
  #               color=MessageColors.NOU))

  #     elif intent in ("Memes", "Memes - Another"):
  #       # reply = ""
  #       kwargs.update(**await get_reddit_post(ctx, ["memes", "dankmemes"]))
  #       # return await msg_reply(ctx, **await get_reddit_post(ctx, ["memes", "dankmemes"]))

  #     elif intent == "Title of your sex tape":
  #       if random.random() < 0.1:
  #         reply = f"*{ctx.clean_content}*, title of your sex-tape"
  #       else:
  #         return

  #     elif intent == "show me something cute":
  #       reply = response
  #       kwargs.update(**await get_reddit_post(ctx, ["mademesmile", "aww"]))
  #       # return await msg_reply(ctx, content=response, **await get_reddit_post(ctx, ["mademesmile", "aww"]))

  #     # elif intent == "what time is it?" or intent == "Math":
  #     #   reply = f"The time is {datetime.datetime.now()}"

  #     elif intent == "Something cool":
  #       kwargs.update(**await get_reddit_post(ctx, ["nextfuckinglevel", "interestingasfuck"]))
  #       # return await msg_reply(ctx, **await get_reddit_post(ctx, ["nextfuckinglevel", "interestingasfuck"]))

  #     elif intent in ("Compliments", "Thanks", "are you a bot?", "I love you"):
  #       hearts = ["❤️", "💯", "💕"]
  #       return await ctx.add_reaction(random.choice(hearts))

  #     elif intent == "give me 5 minutes / hours / time":
  #       clocks = ["⏰", "⌚", "🕰", "⏱"]
  #       return await ctx.add_reaction(random.choice(clocks))

  #     # TODO: Make the inspiration command
  #     elif intent == "inspiration":
  #       print("inspiration")
  #       # await require("../commands/inspiration").execute(msg);

  #     elif intent == "Math":
  #       # // (?:.+)([0-9\+\-\/\*]+)(?:.+)
  #       print("Big math")

  #     # TODO: this
  #     elif intent == "Tell me a joke friday":
  #       print("joke")
  #       # await require("../functions/reddit")(msg, bot, ["Jokes"], "text");

  #     elif intent == "Shit" and ("shit" in ctx.clean_content.lower() or "crap" in ctx.clean_content.lower()):
  #       return await ctx.add_reaction("💩")

  #     elif intent == "How do commands":
  #       reply = "To find all of my commands please use the help command"
  #       # await require("../commands/help")(msg, "", bot);

  #     elif intent == "who am i?":
  #       reply = f"Well I don't know your real name but your username is {ctx.author.name}"

  #     elif intent == "can i invite you to my server":
  #       kwargs.update(embed=embed(title="Here is the link to invite me", description=f"[Invite link]({self.bot.get_cog('Invite').link})"))

  #     elif intent == "doggo":
  #       return await ctx.add_reaction(random.choice(["🐶", "🐕", "🐩", "🐕‍🦺"]))

  #     elif intent == "how old are you? / Age":
  #       now = datetime.datetime.now()
  #       born = self.bot.user.created_at
  #       months = (now.year - born.year) * 12 + (now.month - born.month)
  #       years = (now.year - born.year)
  #       reply = f"I was born on **{born.strftime('%b %d, %Y')}** which would make me **{months if months < 12 else years} {'months' if months < 12 else 'years'}** old"

  #     elif intent == "standing up for me":
  #       return await ctx.add_reaction("♥")

  #     elif intent == "talking about me":
  #       return await ctx.add_reaction("👀")

  #     else:
  #       await relay_info(f"I dont have a response for this: {ctx.content}", self.bot, webhook=self.bot.log.log_chat)
  #   except BaseException:
  #     await msg_reply(ctx, "Something in my code failed to run, I'll ask my boss to fix this :)")
  #     raise
  #     # print(e)
  #     # logging.error(e)
  #   if reply is not None or len(kwargs) > 0:
  #     await msg_reply(ctx, self.translate_request(reply, to_lang=lang).get("translatedText", reply) if lang != 'en' and reply is not None else reply, **kwargs)


def setup(bot):
  ...
  # bot.add_cog(ChatNew(bot))
