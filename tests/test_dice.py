from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

from functions.messagecolors import MessageColors

if TYPE_CHECKING:
  from .conftest import UnitTester
  from discord import TextChannel

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("roll", ["1d20", "2d8", "1d20k7", "1*3", ""])
async def test_dice(bot: UnitTester, channel: TextChannel, roll: str):
  content = f"!dice {roll}"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  if roll == "":
    assert msg.embeds[0].title == "!dice"
  else:
    assert "Your total:" in msg.embeds[0].title and msg.embeds[0].color.value == MessageColors.default().value
