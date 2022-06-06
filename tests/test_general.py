from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from functions.messagecolors import MessageColors

from .conftest import send_command

if TYPE_CHECKING:
  from discord import TextChannel

  from .conftest import Friday, UnitTester

pytestmark = pytest.mark.asyncio


@pytest.mark.dependency()
async def test_get_cog(friday: Friday):
  assert friday.get_cog("General") is not None


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_bot(bot: UnitTester, channel: TextChannel):
  content = "!info"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Friday" in msg.embeds[0].title and "- About" in msg.embeds[0].title
  assert msg.embeds[0].color == MessageColors.default()
  assert len(msg.embeds[0].fields) == 7


@pytest.mark.parametrize("user", ["", "751680714948214855"])
@pytest.mark.dependency(depends=["test_get_cog"])
async def test_user(bot: UnitTester, channel: TextChannel, user: str):
  content = f"!userinfo {user}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Friday" in msg.embeds[0].title and "- Info" in msg.embeds[0].title
  assert len(msg.embeds[0].fields) == 8


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_guild(bot: UnitTester, channel: TextChannel):
  content = "!serverinfo"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"{msg.guild.name if msg.guild is not None and msg.guild.name is not None else 'Diary'} - Info"
  assert len(msg.embeds[0].fields) == 6


@pytest.mark.parametrize("role", ["", "895463648326221854"])
@pytest.mark.dependency(depends=["test_get_cog"])
async def test_role(bot: UnitTester, channel: TextChannel, role: str):
  content = f"!roleinfo {role}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  if role:
    assert "- Info" in msg.embeds[0].title
    assert len(msg.embeds[0].fields) == 7
  else:
    assert msg.embeds[0].title == "!roleinfo"


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_invite(bot: UnitTester, channel: TextChannel):
  content = "!invite"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Invite me :)"
