import pytest
from functions.messagecolors import MessageColors
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel


@pytest.mark.asyncio
async def test_bot(bot: "bot", channel: "channel"):
  content = "!info"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "Friday" in msg.embeds[0].title and "- About" in msg.embeds[0].title and msg.embeds[0].color.value == MessageColors.DEFAULT


@pytest.mark.asyncio
async def test_user(bot: "bot", channel: "channel"):
  content = "!userinfo"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Friday Unit Tester - Info"


@pytest.mark.asyncio
async def test_other_user(bot: "bot", channel: "channel"):
  content = "!userinfo 751680714948214855"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "Friday" in msg.embeds[0].title and "- Info" in msg.embeds[0].title


@pytest.mark.asyncio
async def test_guild(bot: "bot", channel: "channel"):
  content = "!serverinfo"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == f"{msg.guild.name if msg.guild is not None and msg.guild.name is not None else 'Diary'} - Info"
