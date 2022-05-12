from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

from functions.messagecolors import MessageColors

if TYPE_CHECKING:
  from .conftest import UnitTester
  from discord import TextChannel

pytestmark = pytest.mark.asyncio


async def test_meme(bot: UnitTester, channel: TextChannel):
  content = "!meme"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].color.value == MessageColors.meme().value
