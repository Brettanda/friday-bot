from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import UnitTester
  from discord.channel import TextChannel

pytestmark = pytest.mark.asyncio


async def test_support(bot: UnitTester, channel: TextChannel):
  content = "!support"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout / 2)  # type: ignore
  assert msg.content == "https://discord.gg/NTRuFjU"


async def test_donate(bot: UnitTester, channel: TextChannel):
  content = "!donate"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout / 2)  # type: ignore
  assert msg.content == "https://www.patreon.com/bePatron?u=42649008"
