from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

from functions.messagecolors import MessageColors

if TYPE_CHECKING:
  from .conftest import bot, channel

pytestmark = pytest.mark.asyncio


async def test_bot(bot: bot, channel: channel):
  content = "!info"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "Friday" in msg.embeds[0].title and "- About" in msg.embeds[0].title and msg.embeds[0].color.value == MessageColors.DEFAULT


@pytest.mark.parametrize("user", ["", "751680714948214855"])
async def test_user(bot: bot, channel: channel, user: str):
  content = f"!userinfo {user}"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "Friday" in msg.embeds[0].title and "- Info" in msg.embeds[0].title
  assert len(msg.embeds[0].fields) == 8


async def test_guild(bot: bot, channel: channel):
  content = "!serverinfo"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == f"{msg.guild.name if msg.guild is not None and msg.guild.name is not None else 'Diary'} - Info"
