import discord
from discord.ext import commands
from typing import TYPE_CHECKING

from numpy import random
import validators
import datetime

from six.moves.html_parser import HTMLParser
from google.cloud import translate_v2 as translate
from functions import MessageColors, dev_guilds, embed, get_reddit_post, config, msg_reply, relay_info, checks, queryIntents

if TYPE_CHECKING:
  from index import Friday as Bot


class Chat(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot
    if not hasattr(self, "translate_client"):
      self.translate_client = translate.Client()
    self.h = HTMLParser()

    # if not hasattr(self, "chat_spam_control"):
    #   self.chat_spam_control = commands.CooldownMapping.from_cooldown(5, 15.0, commands.BucketType.channel)

  @commands.command(name="say", aliases=["repeat"], description="Make Friday say what ever you want")
  async def say(self, ctx, content: str):
    if content == ("im stupid", "i'm stupid", "i am dumb", "im dumb"):
      return await ctx.reply("yeah we know", allowed_mentions=discord.AllowedMentions(roles=False, everyone=False, users=False))
    await ctx.reply(content, allowed_mentions=discord.AllowedMentions(roles=False, everyone=False, users=False))

  def translate_request(self, text: str, detect=False, from_lang=None, to_lang="en"):
    if from_lang == to_lang:
      return None
    try:
      return self.translate_client.translate(text, source_language=from_lang, target_language=to_lang)
    except Exception as e:
      raise e

  @commands.Cog.listener()
  async def on_message(self, ctx):
    dynamic = False

    lang = self.bot.log.get_guild_lang(ctx.guild)
    tier = self.bot.log.get_guild_tier(ctx.guild)

    if ctx.author.bot and ctx.channel.id != 827656054728818718:
      return
    if ctx.author == self.bot.user and ctx.channel.id != 827656054728818718:
      return
    if ctx.activity is not None:
      return
    if len(ctx.clean_content) > 200:
      return

    if ctx.content == "":
      return

    com_ctx = await self.bot.get_context(ctx)

    if com_ctx.command is not None:
      return

    if ctx.clean_content.startswith(tuple(self.bot.log.get_prefixes())):
      return

    valid = validators.url(ctx.content)
    if valid or ctx.channel.type in [discord.ChannelType.store, discord.ChannelType.voice, discord.ChannelType.category, discord.ChannelType.news]:
      return

    if ctx.guild is not None:
      muted = self.bot.log.get_guild_muted(ctx.guild.id)
      if muted == 1 or muted is True:
        return

    if ctx.type.name != "default":
      return

    if not ctx.content.startswith(tuple(self.bot.log.get_prefixes())):
      noContext = ["Title of your sex tape", "Self Aware", "No U", "I'm dad"]
      lastmessages, lastauthormessages = None, None
      try:
        lastmessages = await ctx.channel.history(limit=3, oldest_first=False).flatten()
        lastauthormessages = [message for message in await ctx.channel.history(limit=5, oldest_first=False).flatten() if message.author.id == ctx.author.id]
      except TimeoutError or discord.DiscordServerError:
        pass
      meinlastmessage = False
      # newest = None

      if len(lastauthormessages) > 2 and lastauthormessages[1].content == ctx.content and ctx.author.id != self.bot.owner_id:
        return

      for msg in lastmessages:
        if msg.author == self.bot.user:
          meinlastmessage = True
          # newest = msg

      translation = {}
      if lang not in (None, "en") or await checks.guild_is_min_tier(self.bot, ctx.guild, "one_guild") or await checks.user_is_min_tier(self.bot, ctx.author, "one_guild"):
        translation = self.translate_request(ctx.clean_content, from_lang=lang if tier == 0 else None)
        if translation.get("translatedText", None) is not None:
          translation["translatedText"] = self.h.unescape(translation["translatedText"])
      original_text = ctx.clean_content

      mentioned = True if "friday" in original_text.lower() or (ctx.reference is not None and ctx.reference.resolved is not None and ctx.reference.resolved.author == self.bot.user) or (ctx.guild is not None and ctx.guild.me in ctx.mentions) else False

      result, intent, chance, inbag, incomingContext, outgoingContext, sentiment = await queryIntents.classify_local(translation.get("translatedText", original_text), mentioned)

      non_trans_result = result

      if result is not None and "dynamic" in result:
        dynamic = True

      if translation.get("detectedSourceLanguage", lang) != "en" and result is not None and "dynamic" not in result:
        final_translation = self.translate_request(result.replace("dynamic", ""), from_lang="en", to_lang=translation.get("detectedSourceLanguage", lang) if translation.get("translatedText") != translation.get("input") else "en")
        if final_translation is not None and final_translation.get("translatedText", None) is not None:
          final_translation["translatedText"] = self.h.unescape(final_translation["translatedText"])
        result = final_translation["translatedText"] if final_translation is not None else result.replace("dynamic", "")
      # elif dynamic and translation.get("detectedSourceLanguage", "en") != "en" and result is not None:
      #   dynamic_translate = True

      # result = translator.translate(result, src="en", dest=translation.src).text if translation.src != "en" and result != "dynamic" else result

      if intent == "Title of your sex tape" and ctx.guild.id not in dev_guilds:
        return await relay_info(f"Not responding with TOYST for: `{ctx.clean_content}`", self.bot, webhook=self.bot.log_chat)

      # TODO: add a check for another bot
      if len([c for c in noContext if intent == c]) == 0 and (self.bot.user not in ctx.mentions) and ("friday" not in ctx.clean_content.lower()) and (meinlastmessage is not True) and (not hasattr(ctx.channel, "type") or ctx.channel.type != "private") and self.bot.log.get_guild_chat_channel(ctx.guild) != ctx.channel.id:
        print("I probably should not respond")
        return
      if result is not None and result != '':
        if self.bot.prod:
          await relay_info("", self.bot, embed=embed(title=f"Intent: {intent}\t{chance}", description=f"| lang: {translation.get('detectedSourceLanguage',None)}\n| original lang: {ctx.guild.preferred_locale.split('-')[0] if ctx.guild is not None else 'en'}\n| sentiment: {sentiment}\n| incoming Context: {incomingContext}\n| outgoing Context: {outgoingContext}\n| input: {ctx.clean_content}\n| translated text: {translation.get('translatedText',original_text)}\n| found in bag: {inbag}\n\t| output: {non_trans_result}\n\\ response: {result}"), webhook=self.bot.log_chat)
        # print(f"Intent: {intent}\t{chance}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content}\n\t| translated text: {translation.get('translatedText',None)}\n\t| found in bag: {inbag}\n\t| output: {non_trans_result}\n\t\\ response: {result}")
        self.bot.logger.info(f"\nIntent: {intent}\t{chance}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content.encode('unicode_escape')}\n\t| translated text: {translation.get('translatedText',None)}\n\t| found in bag: {inbag}\n\t| output: {non_trans_result}\n\t\\ response: {result.encode('unicode_escape')}")
      else:
        # print(f"\nIntent: {intent}\t{chance}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content.encode('unicode_escape')}\n\t| translated text: {translation.get('translatedText', original_text).encode('unicode_escape')}\n\t| found in bag: {inbag}\n\t| output: {non_trans_result}\n\t\\No response found: {ctx.clean_content.encode('unicode_escape')}")
        self.bot.logger.info(f"\nIntent: {intent}\t{chance}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content.encode('unicode_escape')}\n\t| translated text: {translation.get('translatedText', original_text).encode('unicode_escape')}\n\t| found in bag: {inbag}\n\t| output: {non_trans_result}\n\t\\No response found: {ctx.clean_content.encode('unicode_escape')}")
        if "friday" in ctx.clean_content.lower() or self.bot.user in ctx.mentions:
          await relay_info("", self.bot, embed=embed(title="I think i should respond to this", description=f"{original_text}{(' translated to `'+translation.get('translatedText',original_text)+'`') if translation.get('detectedSourceLanguage', 'en') != 'en' else ''}"), webhook=self.bot.log.log_chat)
          # print(f"I think I should respond to this: {original_text}{(' translated to `'+translation.get('translatedText',original_text)+'`') if translation.get('detectedSourceLanguage', 'en') != 'en' else ''}")
          self.bot.logger.info(f"I think I should respond to this: {original_text}{(' translated to `'+translation.get('translatedText',original_text)+'`') if translation.get('detectedSourceLanguage', 'en') != 'en' else ''}")

      if result is not None and result != '':
        if dynamic:
          await self.dynamicchat(ctx, intent, result, lang=lang if tier == 0 else translation.get("detectedSourceLanguage", lang))
        else:
          await msg_reply(ctx, result, mention_author=False)

  async def dynamicchat(self, ctx, intent, response=None, lang=None, **kwargs):
    response = response.replace("dynamic", "")
    # print(f"intent: {intent}")
    # logging.info(f"intent: {intent}")
    reply = None
    try:
      if intent == "Insults":
        return await ctx.add_reaction("😭")

      elif intent == "Activities":
        if ctx.guild.me.activity is not None:
          reply = f"I am playing **{ctx.guild.me.activity.name}**"
        else:
          reply = "I am not currently playing anything. Im just hanging out"

      elif intent == "Self Aware":
        return await ctx.add_reaction("👀")

      elif intent == "Creator / who do you work for?":
        appinfo = await self.bot.application_info()
        reply = f"{appinfo.owner} is my creator :)"

      elif intent == "Soup Time":
        return await ctx.reply(embed=embed(
            title="Here is sum soup, just for you",
            color=MessageColors.SOUPTIME,
            description="I hope you enjoy!",
            image=random.choice(config['soups'])
        ))

      elif intent == "Stop":
        return await ctx.add_reaction("😅")

      elif intent == "No U":
        return await ctx.channel.send(
            embed=embed(
                title="No u!",
                image=random.choice(config["unoCards"]),
                color=MessageColors.NOU))

      elif intent in ("Memes", "Memes - Another"):
        # reply = ""
        kwargs.update(**await get_reddit_post(ctx, ["memes", "dankmemes"]))
        # return await msg_reply(ctx, **await get_reddit_post(ctx, ["memes", "dankmemes"]))

      elif intent == "Title of your sex tape":
        if random.random() < 0.1:
          reply = f"*{ctx.clean_content}*, title of your sex-tape"
        else:
          return

      elif intent == "show me something cute":
        reply = response
        kwargs.update(**await get_reddit_post(ctx, ["mademesmile", "aww"]))
        # return await msg_reply(ctx, content=response, **await get_reddit_post(ctx, ["mademesmile", "aww"]))

      elif intent == "Something cool":
        kwargs.update(**await get_reddit_post(ctx, ["nextfuckinglevel", "interestingasfuck"]))
        # return await msg_reply(ctx, **await get_reddit_post(ctx, ["nextfuckinglevel", "interestingasfuck"]))

      elif intent in ("Compliments", "Thanks", "are you a bot?", "I love you"):
        hearts = ["❤️", "💯", "💕"]
        return await ctx.add_reaction(random.choice(hearts))

      elif intent == "give me 5 minutes / hours / time":
        clocks = ["⏰", "⌚", "🕰", "⏱"]
        return await ctx.add_reaction(random.choice(clocks))

      # TODO: Make the inspiration command
      elif intent == "inspiration":
        print("inspiration")
        # await require("../commands/inspiration").execute(msg);

      elif intent == "Math":
        # // (?:.+)([0-9\+\-\/\*]+)(?:.+)
        print("Big math")

      # TODO: this
      elif intent == "Tell me a joke friday":
        print("joke")
        # await require("../functions/reddit")(msg, bot, ["Jokes"], "text");

      elif intent == "Shit" and ("shit" in ctx.clean_content.lower() or "crap" in ctx.clean_content.lower()):
        return await ctx.add_reaction("💩")

      elif intent == "How do commands":
        reply = "To find all of my commands please use the help command"
        # await require("../commands/help")(msg, "", bot);

      elif intent == "who am i?":
        reply = f"Well I don't know your real name but your username is {ctx.author.name}"

      elif intent == "can i invite you to my server":
        kwargs.update(embed=embed(title="Here is the link to invite me", description=f"[Invite link]({self.bot.get_cog('Invite').link})"))

      elif intent == "doggo":
        return await ctx.add_reaction(random.choice(["🐶", "🐕", "🐩", "🐕‍🦺"]))

      elif intent == "how old are you? / Age":
        now = datetime.datetime.now()
        born = self.bot.user.created_at
        months = (now.year - born.year) * 12 + (now.month - born.month)
        years = (now.year - born.year)
        reply = f"I was born on **{born.strftime('%b %d, %Y')}** which would make me **{months if months < 12 else years} {'months' if months < 12 else 'years'}** old"

      elif intent == "talking about me":
        return await ctx.add_reaction("👀")

      else:
        await relay_info(f"I dont have a response for this: {ctx.content}", self.bot, webhook=self.bot.log.log_chat)
    except BaseException:
      await msg_reply(ctx, "Something in my code failed to run, I'll ask my boss to fix this :)")
      raise
      # print(e)
      # logging.error(e)
    if reply is not None or len(kwargs) > 0:
      await msg_reply(ctx, self.translate_request(reply, to_lang=lang).get("translatedText", reply) if lang != 'en' and reply is not None else reply, **kwargs)


def setup(bot):
  bot.add_cog(Chat(bot))
