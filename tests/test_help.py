from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import UnitTester
  from discord import TextChannel

pytestmark = pytest.mark.asyncio


async def test_help(bot: UnitTester, channel: TextChannel):
  content = "!help"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Friday - Help links"
  # assert len(msg.embeds[0].fields) > 0


async def test_command_unknown(bot: UnitTester, channel: TextChannel):
  content = "!help asd"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == 'No command called "asd" found.'


@pytest.mark.parametrize("command", ["ping", "souptime", "ban", "kick"])
async def test_command(bot: UnitTester, channel: TextChannel, command: str):
  content = f"!help {command}"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"!{command}"


@pytest.mark.parametrize("cog", ["Music", "Moderation", "Dev", "TopGG"])
async def test_cog(bot: UnitTester, channel: TextChannel, cog: str):
  content = f"!help {cog}"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert cog in msg.embeds[0].title
  assert len(msg.embeds[0].fields) > 0


@pytest.mark.parametrize("group", ["blacklist", "custom", "welcome"])
async def test_group(bot: UnitTester, channel: TextChannel, group: str):
  content = f"!help {group}"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"!{group}"
  assert len(msg.embeds[0].fields) > 0


@pytest.mark.parametrize("subcommand", ["blacklist add", "welcome role", "custom add"])
async def test_subcommand(bot: UnitTester, channel: TextChannel, subcommand: str):
  content = f"!help {subcommand}"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"!{subcommand}"
  assert len(msg.embeds[0].fields) > 0
