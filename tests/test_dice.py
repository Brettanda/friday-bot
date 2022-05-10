from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

from functions.messagecolors import MessageColors

if TYPE_CHECKING:
  from .conftest import bot, channel

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("roll", ["1d20", "2d8", "1d20k7", "1*3", ""])
async def test_dice(bot: bot, channel: channel, roll: str):
  content = f"!dice {roll}"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  if roll == "":
    assert msg.embeds[0].title == "!dice"
  else:
    assert "Your total:" in msg.embeds[0].title and msg.embeds[0].color.value == MessageColors.DEFAULT
