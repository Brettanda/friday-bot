from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from functions.messagecolors import MessageColors

if TYPE_CHECKING:
  from discord import TextChannel

  from .conftest import UnitTester

pytestmark = pytest.mark.asyncio


async def test_bot(bot: UnitTester, channel: TextChannel):
  content = "!info"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Friday" in msg.embeds[0].title and "- About" in msg.embeds[0].title
  assert msg.embeds[0].color == MessageColors.default()


@pytest.mark.parametrize("user", ["", "751680714948214855"])
async def test_user(bot: UnitTester, channel: TextChannel, user: str):
  content = f"!userinfo {user}"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Friday" in msg.embeds[0].title and "- Info" in msg.embeds[0].title
  assert len(msg.embeds[0].fields) == 8


async def test_guild(bot: UnitTester, channel: TextChannel):
  content = "!serverinfo"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"{msg.guild.name if msg.guild is not None and msg.guild.name is not None else 'Diary'} - Info"


@pytest.mark.parametrize("role", ["", "895463648326221854"])
async def test_role(bot: UnitTester, channel: TextChannel, role: str):
  content = f"!roleinfo {role}"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  if role:
    assert "- Info" in msg.embeds[0].title
    assert len(msg.embeds[0].fields) == 7
  else:
    assert msg.embeds[0].title == "!roleinfo"
