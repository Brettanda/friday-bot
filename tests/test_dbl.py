from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import UnitTester
  from discord import TextChannel

pytestmark = pytest.mark.asyncio


async def test_vote(bot: UnitTester, channel: TextChannel):
  content = "!vote"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Voting"
