from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import UnitTester
  from discord.channel import TextChannel

pytestmark = pytest.mark.asyncio


async def test_reminders(bot: UnitTester, channel: TextChannel):
  content = "!remind me in 5 minutes to do this"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Reminder set" in msg.embeds[0].title


async def test_reminders_list(bot: UnitTester, channel: TextChannel):
  content = "!remind list"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Reminders"
