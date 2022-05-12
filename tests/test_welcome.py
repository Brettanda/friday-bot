from __future__ import annotations

import pytest
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import UnitTester
  from discord import TextChannel

pytestmark = pytest.mark.asyncio


async def test_welcome(bot: UnitTester, channel: TextChannel):
  content = "!welcome"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  assert "Current Welcome Settings" == msg.embeds[0].title


async def test_display(bot: UnitTester, channel: TextChannel):
  content = "!welcome display"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  assert "Current Welcome Settings" in msg.embeds[0].title


async def test_role(bot: UnitTester, channel: TextChannel):
  content = "!welcome role 895463648326221854"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  content = "!welcome role"
  assert await channel.send(content)
  await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  assert "New members will now receive the role " in msg.embeds[0].title


async def test_channel(bot: UnitTester, channel: TextChannel):
  content = f"!welcome channel {channel.id}"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  content = "!welcome channel"
  assert await channel.send(content)
  await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  assert "Welcome message will be sent to" in msg.embeds[0].title


@pytest.mark.parametrize("args", ["\"this is a message to {user} from {server}\"", ""])
async def test_message(bot: UnitTester, channel: TextChannel, args: str):
  content = f'!welcome message {args}'
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "This servers welcome message is now" or msg.embeds[0].title == "Welcome message removed"


async def test_join_event(bot: UnitTester, channel: TextChannel):
  pytest.skip("Not implemented")
