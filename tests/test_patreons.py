from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from discord.channel import TextChannel

  from .conftest import UnitTester

pytestmark = pytest.mark.asyncio


async def test_patreon(bot: UnitTester, channel: TextChannel):
  content = "!patreon"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Become a Patron!"


async def test_server_activate(bot: UnitTester, channel: TextChannel):
  content = "!patreon server activate"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Your Patronage was not found"


async def test_server_deactivate(bot: UnitTester, channel: TextChannel):
  content = "!patreon server deactivate"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "This command requires a premium server and a patron or a mod."
