# import asyncio
import json
import logging
# import os
# import random
import numpy as np
from googletrans import Translator
# import sys

# from discord.ext import commands

from functions import embed, get_reddit_post, MessageColors, msg_reply

with open('./config.json') as f:
  config = json.load(f)


translator = Translator()


async def dynamicchat(ctx, bot, intent, response=None, lang='en'):
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
      appinfo = await bot.application_info()
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
              image=np.random.choice(config["unoCards"]),
              color=MessageColors.NOU))

    elif intent in ("Memes", "Memes - Another"):
      return await msg_reply(ctx, **await get_reddit_post(ctx, ["memes", "dankmemes"]))

    elif intent == "Title of your sex tape":
      if np.random.random() < 0.1:
        reply = f"*{ctx.clean_content}*, title of your sex-tape"
      else:
        return

    elif intent == "show me something cute":
      return msg_reply(ctx, content=response, **await get_reddit_post(ctx, ["mademesmile", "aww"]))

    elif intent == "Something cool":
      return msg_reply(ctx, **await get_reddit_post(ctx, ["nextfuckinglevel", "interestingasfuck"]))

    elif intent in ("Compliments", "Thanks", "are you a bot?", "I love you"):
      hearts = ["❤️", "💯", "💕"]
      return await ctx.add_reaction(np.random.choice(hearts))

    elif intent == "give me 5 minutes":
      clocks = ["⏰", "⌚", "🕰", "⏱"]
      return await ctx.add_reaction(np.random.choice(clocks))

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
      return await ctx.add_reaction(np.random.choice(["🐶", "🐕", "🐩", "🐕‍🦺"]))

    else:
      print(f"I dont have a response for this: {ctx.content}")
      logging.warning("I dont have a response for this: %s", ctx.clean_content)
  except BaseException:
    await msg_reply(ctx, "Something in my code failed to run, I'll ask my boss to fix this :)")
    raise
    # print(e)
    # logging.error(e)
  await msg_reply(ctx, translator.translate(reply, dest=lang).text if lang != 'en' else reply)
