import logging
import os

import discord


async def relay_info(msg: str, bot: discord.Client or discord.AutoShardedClient, embed: discord.Embed = None, file=None, filefirst=False, short: str = None, webhook: discord.Webhook = None, logger=logging.getLogger(__name__)):
  if webhook is None:
    webhook = bot.log_info
  if bot.prod:
    thispath = os.getcwd()
    if "\\" in thispath:
      seperator = "\\\\"
    else:
      seperator = "/"
    try:
      await webhook.send(username=bot.user.name, avatar_url=bot.user.avatar_url, content=msg, embed=embed if not filefirst else None, file=discord.File(fp=f"{thispath}{seperator}{file}", filename="Error.txt") if filefirst else None)
    except discord.HTTPException:
      await webhook.send(username=bot.user.name, avatar_url=bot.user.avatar_url, file=discord.File(fp=f"{thispath}{seperator}{file}", filename="Error.txt"))
  # elif bot.prod:
  #   appinfo = await bot.application_info()
  #   owner = bot.get_user(appinfo.team.owner.id)
  #   if owner is not None:
  #     if file is not None:
  #       thispath = os.getcwd()
  #       if "\\" in thispath:
  #         seperator = "\\\\"
  #       else:
  #         seperator = "/"
  #       await owner.send(content=msg, embed=embed, file=discord.File(fp=f"{thispath}{seperator}{file}", filename="Error.txt"))
  #     else:
  #       await owner.send(content=msg, embed=embed)
  if short is not None:
    print(short)
    logger.info(short)
  else:
    print(msg)
    logger.info(msg)
