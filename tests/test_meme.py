from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

from functions.messagecolors import MessageColors

if TYPE_CHECKING:
  from .conftest import bot, channel

pytestmark = pytest.mark.asyncio


async def test_meme(bot: bot, channel: channel):
  content = "!meme"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].color.value == MessageColors.MEME
