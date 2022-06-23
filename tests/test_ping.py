from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from .conftest import send_command

if TYPE_CHECKING:
  from discord.channel import TextChannel

  from .conftest import UnitTester

pytestmark = pytest.mark.asyncio


async def test_ping(bot: UnitTester, channel: TextChannel):
  content = "!ping"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Pong!"
  assert "API is" in msg.embeds[0].description
