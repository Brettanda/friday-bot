import logging
import os

import discord
from typing_extensions import TYPE_CHECKING
if TYPE_CHECKING:
  from index import Friday as Bot


async def relay_info(msg: str, bot: "Bot" or discord.AutoShardedClient, embed: discord.Embed = None, file=None, filefirst=False, short: str = None, webhook: discord.Webhook = None, logger=logging.getLogger(__name__)):
  if webhook is None:
    webhook = bot.log.log_info
  if bot.prod or bot.canary:
    thispath = os.getcwd()
    if "\\" in thispath:
      seperator = "\\\\"
    else:
      seperator = "/"
    try:
      await webhook.send(username=bot.user.name, avatar_url=bot.user.avatar_url if hasattr(bot.user, "avatar_url") else None, content=msg, embed=embed if not filefirst else None, file=discord.File(fp=f"{thispath}{seperator}{file}", filename="Error.txt") if filefirst else None)
    except discord.HTTPException:
      await webhook.send(username=bot.user.name, avatar_url=bot.user.avatar_url if hasattr(bot.user, "avatar_url") else None, file=discord.File(fp=f"{thispath}{seperator}{file}", filename="Error.txt"))
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
    bot.logger.info(short)
  else:
    bot.logger.info(msg)
