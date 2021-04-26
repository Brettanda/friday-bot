import logging
import os
import uuid
import json
from numpy import random

import validators
from discord.ext import commands
# from dotenv import load_dotenv

# from chatml import queryGen
from chatml import queryIntents
# from chatml.dynamicchat import dynamicchat
from functions import (dev_guilds, embed, msg_reply, mydb_connect, query,
                       relay_info, get_reddit_post, MessageColors)
from functions.mysql_connection import query_prefix

# from functions import embed, , , msg_reply

with open('./config.json') as f:
  config = json.load(f)

logger = logging.getLogger(__name__)

# load_dotenv()
trans_key = os.environ.get('TRANSLATORKEY')
trans_endpoint = os.environ.get('TRANSLATORENDPOINT')


class Chat(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  async def translate_request(self, text: str, detect=False, params=""):
    headers = {
        'Ocp-Apim-Subscription-Key': trans_key,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }

    body = [{
        'text': text
    }]

    path = f'/{"detect" if detect is True else "translate"}?api-version=3.0'
    url = trans_endpoint + path + params

    async with self.bot.session.post(url, headers=headers, json=body) as r:
      if r.status == 200:
        return await r.json()

  @commands.Cog.listener()
  async def on_message(self, ctx):
    if ctx.author.bot and ctx.channel.id != 827656054728818718:
      return
    if ctx.author == self.bot.user and ctx.channel.id != 827656054728818718:
      return
    if ctx.activity is not None:
      return
    if len(ctx.clean_content) > 200:
      return

    if ctx.clean_content.startswith("/"):
      return

    valid = validators.url(ctx.content)
    if valid or str(ctx.channel.type).lower() in ["store", "voice", "category", "news"]:
      return

    if ctx.guild is not None:
      mydb = mydb_connect()
      muted = query(mydb, "SELECT muted FROM servers WHERE id=%s", ctx.guild.id)
      if muted == 1:
        return

    if ctx.type.name != "default":
      return

    prefix = str(query_prefix(self.bot, ctx, True))
    if not ctx.content.startswith(prefix):
      noContext = ["Title of your sex tape", "I dont want to talk to a chat bot", "The meaning of life?", "Birthday", "Memes", "Self Aware", "Soup Time", "No U", "I'm dad", "Bot discrimination"]
      lastmessages = await ctx.channel.history(limit=3).flatten()
      meinlastmessage = False
      # newest = None
      for msg in lastmessages:
        if msg.author == self.bot.user:
          meinlastmessage = True
          # newest = msg

      detect_response = await self.translate_request(ctx.clean_content, True)

      # detected = json.dumps(response, sort_keys=True, indent=2, ensure_ascii=False, separators=(',', ': '))
      translation_text = ctx.clean_content
      if detect_response[0]["language"] != "en" and detect_response[0]["isTranslationSupported"] is True:
        params = f"&from={detect_response[0]['language']}&to=en"

        translation = await self.translate_request(ctx.clean_content, params=params)

        translation_text = translation[0]["translations"][0]["text"]
      # translation = translator.translate(ctx.clean_content, to_lang="en")

      mentioned = True if "friday" in translation_text or (ctx.reference is not None and ctx.reference.resolved is not None and ctx.reference.resolved.author == self.bot.user) or (ctx.guild is not None and ctx.guild.me in ctx.mentions) else False

      result, intent, chance, inbag, incomingContext, outgoingContext, sentiment = await queryIntents.classify_local(translation_text, mentioned)

      non_trans_result = result

      if detect_response[0]["language"] != "en" and detect_response[0]["isTranslationSupported"] is True:
        params = f"&from=en&to={detect_response[0]['language']}"

        final_translation = await self.translate_request(result, params=params)
        result = final_translation[0]["translations"][0]["text"]

      # result = translator.translate(result, src="en", dest=translation.src).text if translation.src != "en" and result != "dynamic" else result

      if intent == "Title of your sex tape" and ctx.guild.id not in dev_guilds:
        return await relay_info(f"Not responding with TOYST for: `{ctx.clean_content}`", self.bot, webhook=self.bot.log_chat)

      # print(incomingContext,outgoingContext,ctx.reference.resolved if ctx.reference is not None else "No reference")
      # if incomingContext is not None and len(incomingContext) > 0 and (newest is not None or ctx.reference is not None):
      #   # await ctx.guild.chunk(cache=False)
      #   past_message = ctx.reference.resolved if ctx.reference is not None else newest
      #   past_message = await ctx.channel.fetch_message(past_message.reference.message_id)
      #   if past_message is None:
      #     print("Outgoing context message was deleted or not found")
      #     logger.warning("Outgoing context message was deleted or not found")
      #     return
      #   past_result,past_intent,past_chance,past_inbag,past_incomingContext,past_outgoingContext = await queryIntents.classify_local(past_message.clean_content)
      #   past_outgoingContexts = []
      #   for context in past_outgoingContext:
      #     past_outgoingContexts.append(context["name"])
      #   print(incomingContext)
      #   print(past_outgoingContexts)
      #   print(len(past_outgoingContexts) > 0)
      #   print(all(incomingContext) not in past_outgoingContexts)
      #   print([i for i in incomingContext if i not in past_outgoingContexts])
      #   # if len(past_outgoingContexts) > 0 and all(incomingContext) not in past_outgoingContexts:
      #   if len(past_outgoingContexts) > 0 and [i for i in incomingContext if i not in past_outgoingContexts]:
      #     print(f"Requires context, not responding: {ctx.reference.resolved.clean_content if ctx.reference is not None else newest.clean_content}")
      #     return
      # TODO: add a check for another bot
      if len([c for c in noContext if intent == c]) == 0 and (self.bot.user not in ctx.mentions) and ("friday" not in ctx.clean_content.lower()) and (meinlastmessage is not True) and (ctx.channel.type != "private"):
        print("I probably should not respond")
        # if "friday" in ctx.clean_content.lower() or self.bot.user in ctx.mentions:
        #   await relay_info("",self.bot,embed=embed(title="I think i should respond to this",description=f"{ctx.content}"),channel=814349008007856168)
        #   print(f"I think I should respond to this: {ctx.clean_content.lower()}")
        #   logger.info(f"I think I should respond to this: {ctx.clean_content.lower()}")
        return
      if result is not None and result != '':
        if self.bot.prod:
          await relay_info("", self.bot, embed=embed(title=f"Intent: {intent}\t{chance}", description=f"| original lang: {detect_response[0]['language']}\n| sentiment: {sentiment}\n| incoming Context: {incomingContext}\n| outgoing Context: {outgoingContext}\n| input: {ctx.clean_content}\n| translated text: {translation_text}\n| found in bag: {inbag}\n\t| en response: {non_trans_result}\n\\ response: {result}"), webhook=self.bot.log_chat)
        print(f"Intent: {intent}\t{chance}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content}\n\t| translated text: {translation_text}\n\t| found in bag: {inbag}\n\t| en response: {non_trans_result}\n\t\\ response: {result}")
        logger.info(f"\nIntent: {intent}\t{chance}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content}\n\t| translated text: {translation_text}\n\t| found in bag: {inbag}\n\t| en response: {non_trans_result}\n\t\\ response: {result}")
      else:
        print(f"\nIntent: {intent}\t{chance}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content}\n\t| translated text: {translation_text}\n\t| found in bag: {inbag}\n\t| en response: {non_trans_result}\n\t\\No response found: {ctx.clean_content.encode('unicode_escape')}")
        logger.info(f"\nIntent: {intent}\t{chance}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content}\n\t| translated text: {translation_text}\n\t| found in bag: {inbag}\n\t| en response: {non_trans_result}\n\t\\No response found: {ctx.clean_content.encode('unicode_escape')}")
        if "friday" in ctx.clean_content.lower() or self.bot.user in ctx.mentions:
          await relay_info("", self.bot, embed=embed(title="I think i should respond to this", description=f"{ctx.content}"), webhook=self.bot.log_chat)
          print(f"I think I should respond to this: {ctx.clean_content.lower()}{(' translated to `'+detect_response[0]['language']+'`') if detect_response[0]['language'] != 'en' else ''}")
          logger.info(f"I think I should respond to this: {ctx.clean_content.lower()}{(' translated to `'+translation_text+'`') if detect_response[0]['language'] != 'en' else ''}")

      if result is not None and result != '':
        if "dynamic" in result:
          await self.dynamicchat(ctx, intent, result, lang=detect_response[0]['language'])
        else:
          await msg_reply(ctx, result, mention_author=False)

  async def dynamicchat(self, ctx, intent, response=None, lang='en'):
    response = response.strip("dynamic")
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

      elif intent == "Creator":
        appinfo = await self.bot.application_info()
        reply = f"{appinfo.owner} is my creator :)"
      # elif intent == "Soup Time":
      #   const image = soups[random.randint(0, soups.length)];
      #   console.info(`Soup: ${image}`);

      #   await msg.channel.send(
      #     func.embed({
      #       title: "It's time for soup, just for you " + msg.author.username,
      #       color: "#FFD700",
      #       description: "I hope you enjoy, I made it myself :)",
      #       author: msg.author,
      #       image: image,
      #     }),
      #   );
      # }

      elif intent == "Stop":
        return await ctx.add_reaction("😅")

      elif intent == "No U":
        await ctx.channel.send(
            embed=embed(
                title="No u!",
                image=random.choice(config["unoCards"]),
                color=MessageColors.NOU))

      elif intent in ("Memes", "Memes - Another"):
        return await msg_reply(ctx, **await get_reddit_post(ctx, ["memes", "dankmemes"]))

      elif intent == "Title of your sex tape":
        if random.random() < 0.1:
          reply = f"*{ctx.clean_content}*, title of your sex-tape"
        else:
          return

      elif intent == "show me something cute":
        return msg_reply(ctx, content=response, **await get_reddit_post(ctx, ["mademesmile", "aww"]))

      elif intent == "Something cool":
        return msg_reply(ctx, **await get_reddit_post(ctx, ["nextfuckinglevel", "interestingasfuck"]))

      elif intent in ("Compliments", "Thanks", "are you a bot?", "I love you"):
        hearts = ["❤️", "💯", "💕"]
        return await ctx.add_reaction(random.choice(hearts))

      elif intent == "give me 5 minutes":
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
        reply = "To find all of my command please use the help command"
        # await require("../commands/help")(msg, "", bot);

      elif intent == "who am i?":
        reply = f"Well I don't know your real name but your username is {ctx.author.name}"

      elif intent == "doggo":
        return await ctx.add_reaction(random.choice(["🐶", "🐕", "🐩", "🐕‍🦺"]))

      else:
        print(f"I dont have a response for this: {ctx.content}")
        logging.warning("I dont have a response for this: %s", ctx.clean_content)
    except BaseException:
      await msg_reply(ctx, "Something in my code failed to run, I'll ask my boss to fix this :)")
      raise
      # print(e)
      # logging.error(e)
    if reply is not None:
      await msg_reply(ctx, self.translate_request(reply, params=f"&from={lang}&to=en") if lang != 'en' else reply)


def setup(bot):
  bot.add_cog(Chat(bot))
