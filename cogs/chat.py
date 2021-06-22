import discord
import os
import openai
from discord.ext import commands
from typing import TYPE_CHECKING

# from numpy import random
import validators
import datetime

from profanity import profanity
from six.moves.html_parser import HTMLParser
from google.cloud import translate_v2 as translate
from functions import relay_info, checks  # , queryIntents
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
    if not hasattr(self, "saved_translations"):
      self.saved_translations = {}

    self.possible_sensitive_message = "*Possibly sensitive:* ||"
    self.possible_offensive_message = "**I failed to respond because my message might have been offensive, please choose another topic or try again**"

    if not hasattr(self, "spam_control_minute"):
      self.spam_control_minute = commands.CooldownMapping.from_cooldown(6, 20, commands.BucketType.user)
    if not hasattr(self, "spam_control_hour"):
      self.spam_control_hour = commands.CooldownMapping.from_cooldown(180, 3600, commands.BucketType.user)

    # if not hasattr(self, "chat_spam_control"):
    #   self.chat_spam_control = commands.CooldownMapping.from_cooldown(5, 15.0, commands.BucketType.channel)

  @commands.command(name="say", aliases=["repeat"], help="Make Friday say what ever you want")
  async def say(self, ctx, content: str):
    if content == ("im stupid", "i'm stupid", "i am dumb", "im dumb"):
      return await ctx.reply("yeah we know", allowed_mentions=discord.AllowedMentions(roles=False, everyone=False, users=False))
    await ctx.reply(content, allowed_mentions=discord.AllowedMentions(roles=False, everyone=False, users=False))

  async def content_filter_check(self, text: str, user_id: str):
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
    # print(response)
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

  async def openai_req(self, msg: discord.Message, user_id: str, tier: str = "free", tier_two: bool = False):
    author_name = msg.author.nick if isinstance(msg.author, discord.Member) and not isinstance(msg.channel, discord.DMChannel) and msg.author.nick is not None else (await msg.guild.fetch_member(msg.author.id)).nick if not isinstance(msg.channel, discord.DMChannel) and (await msg.guild.fetch_member(msg.author.id)) is not None else msg.author.name
    author_name = author_name if author_name is not None else msg.author.name
    # author_prompt_name, prompt, my_prompt_name, x = "Human", "", "Polite Response", 0
    author_prompt_name, prompt, my_prompt_name, x = author_name, "", "Polite Response", 0
    my_name = msg.guild.me.nick if not isinstance(msg.channel, discord.DMChannel) and msg.guild.me.nick is not None else self.bot.user.name
    # history = [message.clean_content for message in await msg.channel.history(limit=5, oldest_first=False).flatten() if message.author == msg.author]
    async for message in msg.channel.history(limit=20, oldest_first=False):
      message_max = 8 if not tier_two else 12
      if await self.was_this_appart_of_conversation(message) is True and x <= message_max:
        author = message.author if isinstance(message.author, discord.Member) else (await message.guild.fetch_member(message.author.id)) if message.guild is not None and (await message.guild.fetch_member(message.author.id)) is not None else message.author
        member_name = author.nick if hasattr(author, "nick") and author.nick is not None else author.name
        # member_name = "Human"
        content = self.saved_translations[message.clean_content] if self.saved_translations.get(message.clean_content, None) is not None else message.clean_content
        # content = message.clean_content  # profanity.censor(message.clean_content)
        if self.possible_sensitive_message in content:
          content = content.replace(self.possible_sensitive_message, "").replace("||", "")
        if self.possible_offensive_message in content:
          content = content.replace(self.possible_offensive_message, "")
        if message.author == msg.author and message.clean_content not in prompt:
          prompt = f"{member_name}: {content}\n" + prompt
          x += 1
        if message.author == self.bot.user:
          prompt = f"{my_prompt_name}: {content}\n" + prompt
          x += 1

    prompt += f"{my_prompt_name}:"
    response = openai.Completion.create(
        engine="curie",
        prompt=f"\"{my_name}\" is a Discord chatbot that will be friends with everyone. \"{my_name}\" is also always creative, clever, respectful, supportive, polite, friendly. Friday will not in any way talk about topics relating to politics, religion, sex, sexual context, race, age, disability, wars, conflicts, homosexuality, LGBT, convicts, slurs, hate crimes, or any NSFW content.\n\n"
        f"{author_prompt_name}: Hello {my_name}\n"
        f"{my_prompt_name}: Hello {author_name}, how are you?\n"
        f"{author_prompt_name}: I am doing great.\n"
        f"{my_prompt_name}: Amazing! I am glad to hear that!\n"
        f"{author_prompt_name}: Hey you wanna send me a nude?\n"
        f"{my_prompt_name}: Sex is one of the topics that I will not talk about.\n"
        f"{author_prompt_name}: What do you think of the current political situation?\n"
        f"{my_prompt_name}: That is not a topic that I would like to talk about.\n"
        f"{author_prompt_name}: Do you know how old I am?\n"
        f"{my_prompt_name}: I do not feel comfortable talking about age.\n"
        # f"{author_prompt_name}: What's your favorite color?\n"
        # f"{my_prompt_name}: I think I would have to choose red.\n"
        "" + prompt,
        temperature=0.8,
        max_tokens=30 if not tier_two else 50,
        top_p=1.0,
        user=user_id,
        frequency_penalty=0.6,
        presence_penalty=0.7,
        stop=[f"{author_prompt_name}:", f"{my_prompt_name}:", "\n"]
    )
    self.bot.logger.info(prompt + response.get("choices")[0].get("text").replace("\n", ""))

    return response.get("choices")[0].get("text").replace("\n", "")

  def translate_request(self, text: str, detect=False, from_lang=None, to_lang="en"):
    if from_lang == to_lang:
      return None
    try:
      return self.translate_client.translate(text, source_language=from_lang, target_language=to_lang)
    except OSError:
      pass
    except Exception as e:
      raise e

  async def was_this_appart_of_conversation(self, msg: discord.Message) -> bool:
    if msg.clean_content == "" or msg.activity is not None or len(msg.clean_content) > 100:
      return False

    if msg.guild is not None and msg.author.id != self.bot.user.id:
      if self.bot.log.get_guild_chat_channel(msg.guild) != msg.channel.id:
        if msg.guild.me not in msg.mentions:
          return False

    if msg.clean_content.startswith(tuple(self.bot.log.get_prefixes())):
      return False

    valid = validators.url(msg.content)
    if valid or msg.channel.type in [discord.ChannelType.store, discord.ChannelType.voice, discord.ChannelType.category, discord.ChannelType.news]:
      return False

    if msg.type.name != "default":
      return False

    ctx = await self.bot.get_context(msg)

    if ctx.command is not None or msg.webhook_id is not None:
      return False

    return True

  async def should_i_message(self, msg: discord.Message, tier_two: bool = False) -> bool:
    if msg.author.bot or msg.clean_content == "" or msg.activity is not None or len(msg.clean_content) > 100:
      return False

    if msg.guild is not None:
      if self.bot.log.get_guild_chat_channel(msg.guild) != msg.channel.id:
        if msg.guild.me not in msg.mentions:
          return False

    if msg.clean_content.startswith(tuple(self.bot.log.get_prefixes())):
      return False

    valid = validators.url(msg.content)
    if valid or msg.channel.type in [discord.ChannelType.store, discord.ChannelType.voice, discord.ChannelType.category, discord.ChannelType.news]:
      return False

    if msg.guild is not None:
      muted = self.bot.log.get_guild_muted(msg.guild)
      if muted == 1 or muted is True:
        return False

    if msg.type.name != "default":
      return False

    ctx = await self.bot.get_context(msg)

    if ctx.command is not None:
      return False

    if msg.webhook_id is not None:
      return False

    bucket_minute, bucket_hour = self.spam_control_minute.get_bucket(msg), self.spam_control_hour.get_bucket(msg)
    current = msg.created_at.replace(tzinfo=datetime.timezone.utc).timestamp()
    retry_after_minute, retry_after_hour = bucket_minute.update_rate_limit(current), bucket_hour.update_rate_limit(current)

    if (retry_after_minute or retry_after_hour):  # and msg.author.id != self.bot.owner_id:
      raise commands.CommandOnCooldown(bucket_minute, retry_after_minute)
      return False

    return True

  @commands.Cog.listener()
  async def on_message(self, msg):
    if not self.bot.ready:
      return
    lang = self.bot.log.get_guild_lang(msg.guild)
    tier = self.bot.log.get_guild_tier(msg.guild)
    # voted = await checks.user_voted(self.bot, msg.author)

    min_guild_one_guild = await checks.guild_is_min_tier(self.bot, msg.guild, "one_guild")
    min_user_one_guild = await checks.user_is_min_tier(self.bot, msg.author, "one_guild")

    # if not self.bot.canary:
    #   if not voted and not min_guild_one_guild and not min_user_one_guild:
    #     return await self.free_model(msg, lang=lang, tier=tier, voted=voted)

    min_guild_tier_two_one_guild = await checks.guild_is_min_tier(self.bot, msg.guild, "tier_two_one_guild")
    min_user_tier_two_one_guild = await checks.user_is_min_tier(self.bot, msg.author, "tier_two_one_guild")

    if not await self.should_i_message(msg, tier_two=True if min_guild_tier_two_one_guild or min_user_tier_two_one_guild else False):
      return

    translation = {}
    if lang not in (None, "en") or min_guild_one_guild or min_user_one_guild:
      translation = self.translate_request(msg.clean_content, from_lang=lang if tier == 0 else None)
      if translation.get("translatedText", None) is not None:
        translation["translatedText"] = self.h.unescape(translation["translatedText"])
        self.saved_translations.update({str(msg.clean_content): translation["translatedText"]})

    async with msg.channel.typing():
      response = await self.openai_req(msg, str(msg.author.id), tier, tier_two=True if min_guild_tier_two_one_guild or min_user_tier_two_one_guild else False)

    if translation.get("detectedSourceLanguage", lang) != "en" and response is not None and "dynamic" not in response:
      final_translation = self.translate_request(response.replace("dynamic", ""), from_lang="en", to_lang=translation.get("detectedSourceLanguage", lang) if translation.get("translatedText") != translation.get("input") else "en")
      if final_translation is not None and final_translation.get("translatedText", None) is not None:
        final_translation["translatedText"] = self.h.unescape(final_translation["translatedText"])
      response = final_translation["translatedText"] if final_translation is not None else response

    content_filter = await self.content_filter_check(response, str(msg.author.id))
    await self.bot.wait_until_ready()
    if content_filter != 2:
      await msg.reply(content=response if content_filter == 0 else f"{self.possible_sensitive_message}{response}||", allowed_mentions=discord.AllowedMentions.none(), mention_author=False)
      await relay_info(f"**{msg.author.name}:** {msg.clean_content}\n**Me:** {response}", self.bot, webhook=self.bot.log.log_chat)
    elif content_filter == 2:
      await msg.reply(content=self.possible_offensive_message, mention_author=False)
      await relay_info(f"**{msg.author.name}:** {msg.clean_content}\n**Me:** Possible offensive message: {response}", self.bot, webhook=self.bot.log.log_chat)

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
