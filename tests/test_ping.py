from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from discord.channel import TextChannel

  from .conftest import UnitTester

pytestmark = pytest.mark.asyncio


async def test_ping(bot: UnitTester, channel: TextChannel):
  content = "!ping"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Pong!"
