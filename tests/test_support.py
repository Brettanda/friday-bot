from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel

pytestmark = pytest.mark.asyncio


async def test_support(bot: bot, channel: channel):
  content = "!support"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout / 2)
  assert msg.content == "https://discord.gg/NTRuFjU"


async def test_donate(bot: bot, channel: channel):
  content = "!donate"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout / 2)
  assert msg.content == "https://www.patreon.com/bePatron?u=42649008"
