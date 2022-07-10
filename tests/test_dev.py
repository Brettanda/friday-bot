from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from .conftest import send_command, msg_check

if TYPE_CHECKING:
  from discord import TextChannel

  from .conftest import Friday, UnitTester, UnitTesterUser

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("command", ["dev reload", "dev", "dev say", "dev reload all"])
async def test_dev(bot_user: UnitTesterUser, channel_user: TextChannel, command: str):
  content = f"!dev {command}"
  com = await channel_user.send(content)
  assert com

  with pytest.raises(asyncio.TimeoutError):
    await bot_user.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore


@pytest.mark.parametrize("command", ["sudo 813618591878086707 dev", ])
async def test_dev_with_sudo(bot: UnitTester, channel: TextChannel, command: str):
  content = f"!dev {command}"
  com = await send_command(bot, channel, content)

  with pytest.raises(asyncio.TimeoutError):
    await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore


async def test_global_blacklist(bot: UnitTester, bot_user: UnitTesterUser, friday: Friday, channel: TextChannel, channel_user: TextChannel):
  content = "!ping"
  com = await send_command(bot_user, channel_user, content)
  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Pong!"

  content = "!help say"
  com = await send_command(bot_user, channel_user, content)
  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=2.0)
  assert msg.embeds[0].title == "!say"

  content = f"!dev block {bot_user.user.id}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=2.0)
  assert msg.embeds[0].title == f"{bot_user.user.id} has been blocked"
  assert bot_user.user.id in friday.blacklist

  content = "!ping"
  com = await send_command(bot_user, channel_user, content)
  with pytest.raises(asyncio.TimeoutError):
    await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=2.0)

  content = "!help say"
  com = await send_command(bot_user, channel_user, content)
  with pytest.raises(asyncio.TimeoutError):
    await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=2.0)

  content = f"!dev unblock {bot_user.user.id}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=2.0)
  assert msg.embeds[0].title == f"{bot_user.user.id} has been unblocked"
  assert bot_user.user.id not in friday.blacklist
