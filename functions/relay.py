from __future__ import annotations
import logging
import os

import discord
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from index import Friday
  from cogs.log import CustomWebhook

MISSING = discord.utils.MISSING


async def relay_info(
        msg: str,
        bot: Friday,
        embed: discord.Embed = MISSING,
        file: discord.File = MISSING,
        filefirst: bool = MISSING,
        short: str = MISSING,
        webhook: CustomWebhook = MISSING,
        logger=logging.getLogger(__name__)
):
  if webhook is MISSING:
    webhook = bot.log.log_info
  if bot.prod or bot.canary:
    await bot.wait_until_ready()
    thispath = os.getcwd()
    if "\\" in thispath:
      seperator = "\\\\"
    else:
      seperator = "/"
    avatar_url = bot.user.display_avatar.url
    await webhook.safe_send(username=bot.user.name, avatar_url=avatar_url, content=msg, embed=embed if not filefirst else MISSING, file=discord.File(f"{thispath}{seperator}{file}", filename="Error.txt") if filefirst else MISSING)

  if short is not MISSING:
    bot.logger.info(short)
  else:
    bot.logger.info(msg)
