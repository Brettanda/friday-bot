import logging
import os

import discord
from typing_extensions import TYPE_CHECKING
if TYPE_CHECKING:
  from index import Friday as Bot

MISSING = discord.utils.MISSING


async def relay_info(msg: str, bot: "Bot", embed: discord.Embed = MISSING, file=MISSING, filefirst=MISSING, short: str = MISSING, webhook: discord.Webhook = MISSING, logger=logging.getLogger(__name__)):
  if webhook is MISSING:
    webhook = bot.log.log_info
  if bot.prod or bot.canary:
    thispath = os.getcwd()
    if "\\" in thispath:
      seperator = "\\\\"
    else:
      seperator = "/"
    avatar_url = bot.user.avatar.url
    try:
      await webhook.send(username=bot.user.name, avatar_url=avatar_url, content=discord.utils.escape_mentions(msg), embed=embed if not filefirst else MISSING, file=discord.File(f"{thispath}{seperator}{file}", filename="Error.txt") if filefirst else MISSING)
    except discord.HTTPException as e:
      bot.logger.error(e)
      await webhook.send(username=bot.user.name, avatar_url=avatar_url, file=discord.File(f"{thispath}{seperator}{file}", filename="Error.txt"))
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
  if short is not MISSING:
    bot.logger.info(short)
  else:
    bot.logger.info(msg)
