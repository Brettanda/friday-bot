from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from functions.messagecolors import MessageColors

from .conftest import send_command, msg_check

if TYPE_CHECKING:
  from discord import TextChannel

  from .conftest import Friday, UnitTester

pytestmark = pytest.mark.asyncio


@pytest.mark.dependency()
async def test_get_cog(friday: Friday):
  assert friday.get_cog("Dice") is not None


@pytest.mark.parametrize("roll", ["1d20", "2d8", "1d20k7", "1*3", ""])
@pytest.mark.dependency(depends=["test_get_cog"])
async def test_dice(bot: UnitTester, channel: TextChannel, roll: str):
  content = f"!dice {roll}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  if roll == "":
    assert msg.embeds[0].title == "!dice"
  else:
    assert "Your total:" in msg.embeds[0].title and msg.embeds[0].color.value == MessageColors.default().value
