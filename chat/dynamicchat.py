import os,sys,logging,asyncio,discord
sys.path.insert(1, os.path.join(sys.path[0], '..'))
from functions import *

import json,random

with open('./config.json') as f:
  config = json.load(f)

async def dynamicchat(ctx,bot,intent):
  # print(f"intent: {intent}")
  # logging.info(f"intent: {intent}")
  try:
    if intent == "Insults":
      await ctx.add_reaction("😭")

    elif intent == "Activities":
      await ctx.reply(f"I am playing **{bot.guilds[0].get_member(bot.user.id).activity.name}**")

    elif intent == "Self Aware":
      await ctx.add_reaction("👀")

    elif intent == "Creator":
      appinfo = await bot.application_info()
      await ctx.reply(f"{appinfo.owner} is my creator :)")
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
      await ctx.add_reaction("😅")

    elif intent == "No U":
      await ctx.channel.send(embed=embed(title="No u!",image=config["unoCards"][random.randint(0,len(config["unoCards"]))],color=MessageColors.NOU))
      # await msg.channel.send(func.embed({ title: "No u!", color: "#FFD700", author: msg.author, image: unoCards[random.randint(0, unoCards.length)] }));

    elif intent == "Memes" or intent == "Memes - Another":
      await ctx.reply(**await get_reddit_post(ctx,["memes","dankmemes"]))

    elif intent == "Title of your sex tape":
      await ctx.reply(f"*{ctx.content}*, title of your sex-tape")
      # msg.channel.send(`*"${func.capitalize(msg.cleanContent)}"*, title of your sex-tape`);

    # TODO: Make the command for this
    elif intent == "show me something cute":
      await ctx.reply(**await get_reddit_post(ctx,["mademesmile"]))

    elif intent == "Something cool":
      await ctx.reply(**await get_reddit_post(ctx,["nextfuckinglevel","interestingasfuck"]))

    elif intent == "Compliments" or intent == "Thanks" or intent == "are you a bot?" or intent == "I love you":
      hearts = ["❤️", "💯", "💕"]
      await ctx.add_reaction(hearts[random.randint(0, len(hearts) - 1)])

    elif intent == "give me 5 minutes":
      clocks = ["⏰", "⌚", "🕰", "⏱"]
      await ctx.add_reaction(clocks[random.randint(0, len(clocks) - 1)])

    # TODO: Make the inspiration command
    elif intent == "inspiration":
      print("inspiration")
      # await require("../commands/inspiration").execute(msg);

    elif intent == "Math":
      # // (?:.+)([0-9\+\-\/\*]+)(?:.+)
      print("Big math")
      # await require("../commands/diceRoll").execute(msg, [result.parameters.fields.Equations.stringValue]);

    # TODO: this
    elif intent == "Tell me a joke friday":
      print("joke")
      # await require("../functions/reddit")(msg, bot, ["Jokes"], "text");

    elif intent == "Shit":
      # if content.includes("shit") or content.includes("shît") or content.includes("crap") or content.includes("poop") or content.includes("poo"):
      await ctx.add_reaction("💩")

    elif intent == "How do commands":
      await ctx.reply("To find all of my command please use the help command")
      # await require("../commands/help")(msg, "", bot);

    elif intent == "who am i?":
      await ctx.reply(f"Well I don't know your real name but your username is {ctx.author.name}")
      # ctx.channel.send(`Well I don't know your real name but your username is ${msg.author.username}`);

    elif intent == "doggo":
      await ctx.add_reaction(random.choice(["🐶","🐕","🐩","🐕‍🦺"]))

    else:
      print(f"I dont have a response for this: {ctx.content}")
      logging.warning(f"I dont have a response for this: {ctx.content}")
  except:
    await ctx.reply("Something in my code failed to run, I'll ask my boss to fix this :)")
    raise
    # print(e)
    # logging.error(e)