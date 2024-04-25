from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from .conftest import send_command, msg_check

if TYPE_CHECKING:
  from discord.channel import TextChannel

  from .conftest import Friday, UnitTester


pytestmark = pytest.mark.asyncio


@pytest.mark.dependency()
async def test_get_cog(friday: Friday):
  assert friday.get_cog("Reminder") is not None


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_reminders(bot: UnitTester, channel: TextChannel):
  content = "!remind me in 5 minutes to do this"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Reminder set" in msg.embeds[0].title


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_reminders_list(bot: UnitTester, channel: TextChannel):
  content = "!remind list"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Reminders"
