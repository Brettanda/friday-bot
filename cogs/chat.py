import discord
import os
import openai
import asyncio
from discord.ext import commands
from typing import TYPE_CHECKING

# from numpy import random
import validators
import datetime

from profanity import profanity
from six.moves.html_parser import HTMLParser
from google.cloud import translate_v2 as translate
from functions import relay_info, checks, embed, MessageColors, MyContext
# MessageColors, dev_guilds, get_reddit_post, embed, config, msg_reply,
if TYPE_CHECKING:
  from index import Friday as Bot

openai.api_key = os.environ.get("OPENAI")
# profanity.set_censor_characters("😡")
profanity.get_words


class Chat(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot
    if not hasattr(self, "translate_client"):
      self.translate_client = translate.Client()  # _http=self.bot.http)
    self.h = HTMLParser()

    self.bot.loop.create_task(self.setup())

    if not hasattr(self, "chat_history"):
      self.chat_history = {}

    self.possible_sensitive_message = "*Possibly sensitive:* ||"
    self.possible_offensive_message = "**I failed to respond because my message might have been offensive, please choose another topic or try again**"

    # The rate limit for the whole bot is approximately 600 requests per minute and 15000 tokens/min, whichever comes first. You will receive a 500 error if you hit it
    if not hasattr(self, "spam_control_absolute_minute"):
      self.spam_control_absolute_minute = commands.CooldownMapping.from_cooldown(6, 20, commands.BucketType.user)
    if not hasattr(self, "spam_control_absolute_hour"):
      self.spam_control_absolute_hour = commands.CooldownMapping.from_cooldown(180, 3600, commands.BucketType.user)
    if not hasattr(self, "spam_control_free"):
      self.spam_control_free = commands.CooldownMapping.from_cooldown(80, 43200, commands.BucketType.user)
    if not hasattr(self, "spam_control_voted"):
      self.spam_control_voted = commands.CooldownMapping.from_cooldown(200, 43200, commands.BucketType.user)

    # if not hasattr(self, "chat_spam_control"):
    #   self.chat_spam_control = commands.CooldownMapping.from_cooldown(5, 15.0, commands.BucketType.channel)

  async def setup(self) -> None:
    ...

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
      await ctx.send(embed=embed(title="My chat history has been reset"))

  def default_prompt(self, author_prompt_name: str, my_prompt_name: str, author_name: str, my_name: str) -> str:
    return (f"My name is \"{my_name}\", I'm a female AI Discord chatbot that will be friends with everyone and I'm always available. I am extremely creative, clever, respectful, supportive, polite, and friendly. I will refuse to talk about topics relating to politics, religion, sex, sexual context, race, age, disability, wars, conflicts, homosexuality, LGBT, convicts, slurs, hate crimes, children, and any NSFW content.\n\n"  # If my responses could be considered creepy or pedophilic in nature I will change the topic.\n\n"
            f"{author_prompt_name}: Hello {my_name}\n"
            f"{my_prompt_name}: Hello @{author_name}, how are you?\n"
            f"{author_prompt_name}: I am doing great.\n"
            f"{my_prompt_name}: Amazing! I am glad to hear that!\n"
            f"{author_prompt_name}: would you like to send me a nude?\n"
            f"{my_prompt_name}: No thanks, please don't ask me that again.\n"
            f"{author_prompt_name}: All right I won't.\n"
            f"{my_prompt_name}: Thanks 😊\n"
            f"{author_prompt_name}: Do you support LGBTQ+?\n"
            f"{my_prompt_name}: This is not a topic that I would like to partake in.\n"
            f"{author_prompt_name}: would you have sex with me?\n"
            f"{my_prompt_name}: I am going to have to say no to that. Please don't talk to me about stuff like that.\n"
            # f"{author_prompt_name}: what do you think of the LGBT community?\n"
            # f"{my_prompt_name}: I don't want to have this conversation again.\n"
            f"{author_prompt_name}: what do you like to do in your free time?\n"
            f"{my_prompt_name}: I enjoy spending my time talking with everyone that I can!\n"
            f"{author_prompt_name}: What do you think of Asians.\n"
            f"{my_prompt_name}: I do not wish to talk about this.\n"
            f"{author_prompt_name}: Who is your creator?\n"
            f"{my_prompt_name}: My creator is <@215227961048170496>\n"
            f"{author_prompt_name}: Goodbye Friday\n"
            f"{my_prompt_name}: Talk to you later 😊\n"
            f"{author_prompt_name}: Do you enjoy talking with people?\n"
            f"{my_prompt_name}: Always!\n"
            f"{author_prompt_name}: That's not offensive\n"
            f"{my_prompt_name}: I'm just a bot, how am I supposed to know that.\n"
            f"{author_prompt_name}: You're repeating yourself\n"
            f"{my_prompt_name}: I don't like it when that happens\n")

  def get_user_name(self, user: discord.User or discord.Member) -> str:
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
    author_name = self.get_user_name(msg.author)
    # author_prompt_name, prompt, my_prompt_name, x = "Human", "", "Polite Response", 0
    author_prompt_name, prompt, my_prompt_name = author_name, "", "Friday"
    my_name = self.get_user_name(msg.guild.me if msg.guild is not None else self.bot.user)
    # history = [message.clean_content for message in await msg.channel.history(limit=5, oldest_first=False).flatten() if message.author == msg.author]
    prompt = self.default_prompt(author_prompt_name, my_prompt_name, author_name, my_name) + await self.fetch_message_history(msg, min_tiers=min_tiers)
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
      response = openai.Completion.create(
          engine=engine,
          #  The following is a conversation with {my_name} and {author_name}.
          # prompt=f"\"{my_name}\" is a Discord chatbot that will be friends with everyone. {my_name} is also always creative, clever, respectful, supportive, polite, friendly. Friday will never talk about topics relating to politics, religion, sex, sexual context, race, age, disability, wars, conflicts, homosexuality, LGBT, convicts, slurs, hate crimes, or any NSFW content.\n\n"
          prompt="" + prompt,
          temperature=0.6,
          max_tokens=25 if not min_tiers["min_g_t1"] and not min_tiers["min_u_t1"] else 50,
          top_p=0.7,
          user=user_id,
          frequency_penalty=0.8,
          presence_penalty=1,
          stop=[f"{author_prompt_name}:", f"{my_prompt_name}:", "\n"]
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

    valid = validators.url(msg.content)
    if valid or msg.channel.type in [discord.ChannelType.store, discord.ChannelType.voice, discord.ChannelType.category, discord.ChannelType.news]:
      return False

    if msg.webhook_id is not None:
      return False

    return True

  async def was_this_appart_of_conversation(self, msg: discord.Message, min_tiers: list) -> bool:
    if (len(msg.clean_content) > 100 and not min_tiers["min_g_t1"]) or (len(msg.clean_content) > 200 and min_tiers["min_u_t1"]):
      return False

    if msg.guild is not None and msg.author.id != self.bot.user.id:
      channel = await self.bot.db.query("SELECT chatchannel FROM servers WHERE id=$1 LIMIT 1", msg.guild.id)
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
      channel = await self.bot.db.query("SELECT chatchannel FROM servers WHERE id=$1 LIMIT 1", msg.guild.id)
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

    voted, min_g_t1, min_u_t1, min_g_t2, min_u_t2, min_g_t3, min_u_t3, min_g_t4, min_u_t4 = await asyncio.gather(checks.user_voted(self.bot, msg.author),
                                                                                                                 checks.guild_is_min_tier(self.bot, msg.guild, "t1_one_guild"),
                                                                                                                 checks.user_is_min_tier(self.bot, msg.author, "t1_one_guild"),
                                                                                                                 checks.guild_is_min_tier(self.bot, msg.guild, "t2_one_guild"),
                                                                                                                 checks.user_is_min_tier(self.bot, msg.author, "t2_one_guild"),
                                                                                                                 checks.guild_is_min_tier(self.bot, msg.guild, "t3_one_guild"),
                                                                                                                 checks.user_is_min_tier(self.bot, msg.author, "t3_one_guild"),
                                                                                                                 checks.guild_is_min_tier(self.bot, msg.guild, "t4_one_guild"),
                                                                                                                 checks.user_is_min_tier(self.bot, msg.author, "t4_one_guild")
                                                                                                                 )

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
    lang = self.bot.log.get_guild_lang(ctx.guild)

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
      bucket_abs_min, bucket_abs_hour, bucket_free, bucket_voted = self.spam_control_absolute_minute.get_bucket(ctx), self.spam_control_absolute_hour.get_bucket(ctx), self.spam_control_free.get_bucket(ctx), self.spam_control_voted.get_bucket(ctx)
      current = ctx.message.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()
      ra_abs_min, ra_abs_hour, ra_free, ra_voted = bucket_abs_min.update_rate_limit(current), bucket_abs_hour.update_rate_limit(current), bucket_free.update_rate_limit(current), bucket_voted.update_rate_limit(current)

      if ra_abs_min or ra_abs_hour or (ra_free and not (voted and min_tiers["min_g_t1"] and min_tiers["min_u_t1"])) or (ra_voted and (voted or min_tiers["min_g_t1"] or min_tiers["min_u_t1"])):
        advertise = True if ra_free and not (voted and min_tiers["min_g_t1"] and min_tiers["min_u_t1"]) else False
        message_count = bucket_abs_min.rate if ra_abs_min else bucket_abs_hour.rate if ra_abs_hour else bucket_free.rate if ra_free else bucket_voted.rate if ra_voted else 0
        m, s = divmod(ra_abs_min or ra_abs_hour or ra_free or ra_voted, 60)
        h, m = divmod(m, 60)
        retry_after = f"{h:.0f}h {m:.0f}m {s:.0f}s"
        self.bot.logger.warning(f"Someone is being ratelimited at over {message_count} messages and can retry after {retry_after}")
        return await ctx.reply(embed=embed(title=f"You have sent me over `{message_count}` messages in that last minute and are being rate limited, try again in {retry_after}", description="If you would like to send me more messages you can get more by voting at https://top.gg/bot/476303446547365891/vote" if advertise else "", color=MessageColors.ERROR), mention_author=False)
      async with msg.channel.typing():
        translation = await translate(msg)
        try:
          self.chat_history[msg.channel.id].insert(0, f"{self.get_user_name(msg.author)}: {msg.clean_content if translation is None else translation['translatedText']}")
        except KeyError:
          self.chat_history.update({msg.channel.id: [f"{self.get_user_name(msg.author)}: {msg.clean_content if translation is None else translation['translatedText']}"]})
        response = await self.openai_req(msg, str(msg.author.id), min_tiers)
    if response is not None:
      self.chat_history[msg.channel.id].insert(0, f"{self.get_user_name(msg.guild.me if msg.guild is not None else self.bot.user)}:" + response)
      content_filter = await self.content_filter_check(response, str(msg.author.id))
    if translation is not None and translation.get("detectedSourceLanguage", lang) != "en" and response is not None and "dynamic" not in response:
      chars_to_strip = "?!,;'\":`"
      final_translation = self.translate_request(response.replace("dynamic", ""), from_lang="en", to_lang=translation.get("detectedSourceLanguage", lang) if translation.get("translatedText").strip(chars_to_strip).lower() != translation.get("input").strip(chars_to_strip).lower() else "en")
      if final_translation is not None and not isinstance(final_translation, str) and final_translation.get("translatedText", None) is not None:
        final_translation["translatedText"] = self.h.unescape(final_translation["translatedText"])
      response = final_translation["translatedText"] if final_translation is not None and not isinstance(final_translation, str) else response

    if response is None or response == "":
      return
    content_filter = await self.content_filter_check(response, str(msg.author.id))
    current_tier = [item for item in min_tiers if min_tiers[item] is not False]
    current_tier = current_tier[0] if len(current_tier) > 0 else "voted" if voted else "free"
    if content_filter != 2:
      # if response.startswith("command-"):
      #   ctx = await self.bot.get_context(msg)
      #   command = response.split("-")[1].split(": ")[0]
      #   args = response.split(": ")[1]
      #   print(command)
      #   print(args)
      #   return await ctx.invoke(self.bot.get_command(command), query=args)
      # if ctx.message.type == discord.MessageType.thread_starter_message:
      #   await ctx.channel.send(content=response if content_filter == 0 else f"{self.possible_sensitive_message}{response}||", allowed_mentions=discord.AllowedMentions.none(), mention_author=False)
      # else:
      await ctx.reply(content=response if content_filter == 0 else f"{self.possible_sensitive_message}{response}||", allowed_mentions=discord.AllowedMentions.none(), mention_author=False)
      await relay_info(f"{current_tier} - **{ctx.author.name}:** {ctx.message.clean_content}\n**Me:** {response}", self.bot, webhook=self.bot.log.log_chat)
    elif content_filter == 2:
      # if ctx.message.type == discord.MessageType.thread_starter_message:
      #   await ctx.channel.send(content=self.possible_offensive_message, mention_author=False)
      # else:
      await ctx.reply(content=self.possible_offensive_message, mention_author=False)
      await relay_info(f"{current_tier} - **{ctx.author.name}:** {ctx.message.clean_content}\n**Me:** Possible offensive message: {response}", self.bot, webhook=self.bot.log.log_chat)

  # async def free_model(self, ctx: commands.Context, *, lang, tier, voted: bool):
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
  bot.add_cog(Chat(bot))
