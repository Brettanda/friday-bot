from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import UnitTester, channel

pytestmark = pytest.mark.asyncio


async def test_help(bot: UnitTester, channel: channel):
  content = "!help"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Friday - Help links"
  # assert len(msg.embeds[0].fields) > 0


async def test_command_unknown(bot, channel):
  content = "!help asd"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == 'No command called "asd" found.'


@pytest.mark.parametrize("command", ["ping", "souptime", "ban", "kick"])
async def test_command(bot, channel, command: str):
  content = f"!help {command}"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"!{command}"


@pytest.mark.parametrize("cog", ["Music", "Moderation", "Dev", "TopGG"])
async def test_cog(bot, channel, cog: str):
  content = f"!help {cog}"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  assert cog in msg.embeds[0].title
  assert len(msg.embeds[0].fields) > 0


@pytest.mark.parametrize("group", ["blacklist", "custom", "welcome"])
async def test_group(bot: UnitTester, channel: channel, group: str):
  content = f"!help {group}"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"!{group}"
  assert len(msg.embeds[0].fields) > 0


@pytest.mark.parametrize("subcommand", ["blacklist add", "welcome role", "custom add"])
async def test_subcommand(bot: UnitTester, channel: channel, subcommand: str):
  content = f"!help {subcommand}"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"!{subcommand}"
  assert len(msg.embeds[0].fields) > 0
