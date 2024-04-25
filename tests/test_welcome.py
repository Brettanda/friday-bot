from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
  from .conftest import UnitTester, Friday
  from discord import TextChannel

from .conftest import send_command, msg_check

pytestmark = pytest.mark.asyncio


@pytest.mark.dependency()
async def test_get_cog(friday: Friday):
  assert friday.get_cog("Welcome") is not None


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_welcome(bot: UnitTester, channel: TextChannel):
  content = "!welcome"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Current Welcome Settings" == msg.embeds[0].title


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_display(bot: UnitTester, channel: TextChannel):
  content = "!welcome display"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Current Welcome Settings" in msg.embeds[0].title


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_role(bot: UnitTester, channel: TextChannel):
  content = "!welcome role 895463648326221854"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  content = "!welcome role"
  com = await send_command(bot, channel, content)
  await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "New members will now receive the role " in msg.embeds[0].title


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_channel(bot: UnitTester, channel: TextChannel):
  content = f"!welcome channel {channel.id}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  content = "!welcome channel"
  com = await send_command(bot, channel, content)
  await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Welcome message will be sent to" in msg.embeds[0].title


@pytest.mark.parametrize("args", ["\"this is a message to {user} from {server}\"", ""])
@pytest.mark.dependency(depends=["test_get_cog"])
async def test_message(bot: UnitTester, channel: TextChannel, args: str):
  content = f'!welcome message {args}'
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "This servers welcome message is now" or msg.embeds[0].title == "Welcome message removed"


@pytest.mark.skip("Not implemented")
@pytest.mark.dependency(depends=["test_get_cog"])
async def test_join_event(bot: UnitTester, channel: TextChannel):
  ...
