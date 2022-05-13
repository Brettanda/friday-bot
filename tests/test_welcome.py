from __future__ import annotations

import pytest
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import UnitTester
  from discord import TextChannel

pytestmark = pytest.mark.asyncio


async def test_welcome(bot: UnitTester, channel: TextChannel):
  content = "!welcome"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Current Welcome Settings" == msg.embeds[0].title


async def test_display(bot: UnitTester, channel: TextChannel):
  content = "!welcome display"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Current Welcome Settings" in msg.embeds[0].title


async def test_role(bot: UnitTester, channel: TextChannel):
  content = "!welcome role 895463648326221854"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  content = "!welcome role"
  com = await channel.send(content)
  assert com
  await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "New members will now receive the role " in msg.embeds[0].title


async def test_channel(bot: UnitTester, channel: TextChannel):
  content = f"!welcome channel {channel.id}"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  content = "!welcome channel"
  com = await channel.send(content)
  assert com
  await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Welcome message will be sent to" in msg.embeds[0].title


@pytest.mark.parametrize("args", ["\"this is a message to {user} from {server}\"", ""])
async def test_message(bot: UnitTester, channel: TextChannel, args: str):
  content = f'!welcome message {args}'
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "This servers welcome message is now" or msg.embeds[0].title == "Welcome message removed"


@pytest.mark.skip("Not implemented")
async def test_join_event(bot: UnitTester, channel: TextChannel):
  ...
