import logging

# import discord
import validators
from discord.ext import commands
from googletrans import Translator

# from chatml import queryGen
from chatml import queryIntents
from chatml.dynamicchat import dynamicchat
from functions import dev_guilds, embed, mydb_connect, query, relay_info, msg_reply
from functions.mysql_connection import query_prefix

logger = logging.getLogger(__name__)
translator = Translator()


class Chat(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.Cog.listener()
  async def on_message(self, ctx):
    if ctx.author.bot and ctx.channel.id != 827656054728818718:
      return
    if ctx.author == self.bot.user and ctx.channel.id != 827656054728818718:
      return
    if ctx.activity is not None:
      return
    if len(ctx.clean_content) > 256:
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

      translation = translator.translate(ctx.clean_content)

      result, intent, chance, inbag, incomingContext, outgoingContext, sentiment = await queryIntents.classify_local(translation.text)

      non_trans_result = result
      result = translator.translate(result, dest=translation.src).text if translation.src != "en" and result != "dynamic" else result

      if intent == "Title of your sex tape" and ctx.guild.id not in dev_guilds:
        return await relay_info(f"Not responding with TOYST for: `{ctx.clean_content}`", self.bot, channel=814349008007856168)

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
          await relay_info("", self.bot, embed=embed(title=f"Intent: {intent}\t{chance}", description=f"| original lang: {translation.src}\n| sentiment: {sentiment}\n| incoming Context: {incomingContext}\n| outgoing Context: {outgoingContext}\n| input: {ctx.clean_content}\n| translated text: {translation}\n| found in bag: {inbag}\n\t| en response: {non_trans_result}\n\\ response: {result}"), channel=814349008007856168)
        print(f"Intent: {intent}\t{chance}\n\t| original lang: {translation.src}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content}\n\t| translated text: {translation.text}\n\t| found in bag: {inbag}\n\t| en response: {non_trans_result}\n\t\\ response: {result}")
        logger.info(f"\nIntent: {intent}\t{chance}\n\t| original lang: {translation.src}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content}\n\t| translated text: {translation}\n\t| found in bag: {inbag}\n\t| en response: {non_trans_result}\n\t\\ response: {result}")
      else:
        print(f"\nIntent: {intent}\t{chance}\n\t| original lang: {translation.src}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content}\n\t| translated text: {translation}\n\t| found in bag: {inbag}\n\t| en response: {non_trans_result}\n\t\\No response found: {ctx.clean_content.encode('unicode_escape')}")
        logger.info(f"\nIntent: {intent}\t{chance}\n\t| original lang: {translation.src}\n\t| sentiment: {sentiment}\n\t| incoming Context: {incomingContext}\n\t| outgoing Context: {outgoingContext}\n\t| input: {ctx.clean_content}\n\t| translated text: {translation}\n\t| found in bag: {inbag}\n\t| en response: {non_trans_result}\n\t\\No response found: {ctx.clean_content.encode('unicode_escape')}")
        if "friday" in ctx.clean_content.lower() or self.bot.user in ctx.mentions:
          await relay_info("", self.bot, embed=embed(title="I think i should respond to this", description=f"{ctx.content}"), channel=814349008007856168)
          print(f"I think I should respond to this: {ctx.clean_content.lower()}{(' translated to `'+translation.text+'`') if translation.src != 'en' else ''}")
          logger.info(f"I think I should respond to this: {ctx.clean_content.lower()}{(' translated to `'+translation.text+'`') if translation.src != 'en' else ''}")

      if result is not None and result != '':
        if "dynamic" in result:
          await dynamicchat(ctx, self.bot, intent, result, translation.src)
        else:
          await msg_reply(ctx, result, mention_author=False)


def setup(bot):
  bot.add_cog(Chat(bot))
