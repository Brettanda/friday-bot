from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from .conftest import send_command

if TYPE_CHECKING:
  from discord.channel import TextChannel

  from .conftest import UnitTester

pytestmark = pytest.mark.asyncio


async def test_patreon(bot: UnitTester, channel: TextChannel):
  content = "!patreon"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Become a Patron!"


async def test_server_patron_activate(bot: UnitTester, channel: TextChannel):
  content = "!dev sudo 813618591878086707 patreon server activate"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "You have upgraded this server to premium"


async def test_server_patron_deactivate(bot: UnitTester, channel: TextChannel):
  content = "!dev sudo 813618591878086707 patreon server deactivate"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "You have successfully removed your server"


async def test_server_activate(bot: UnitTester, channel: TextChannel):
  content = "!patreon server activate"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Your Patronage was not found"


async def test_server_deactivate(bot: UnitTester, channel: TextChannel):
  content = "!patreon server deactivate"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "This is not a premium server"
