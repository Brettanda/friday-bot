from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import UnitTester
  from discord import TextChannel

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("words", ["hey bruh", '"big bruh moment"', "welcome"])
async def test_say(bot: UnitTester, channel: TextChannel, words: str):
  content = f"!say {words}"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.content == words


async def test_say_no_argument(bot: UnitTester, channel: TextChannel):
  content = "!say"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "!say"


async def test_chatchannel(bot: UnitTester, channel: TextChannel):
  content = "!chatchannel"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Current chat channel"
  assert msg.embeds[0].description


async def test_chatchannel_set(bot: UnitTester, channel: TextChannel):
  content = "!chatchannel 892840236781015120"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Chat channel set"


async def test_chatchannel_voice_channel(bot: UnitTester, channel: TextChannel):
  content = "!chatchannel 895486009465266176"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Channel \"895486009465266176\" not found."


async def test_chatchannel_clear(bot: UnitTester, channel: TextChannel):
  content = "!chatchannel clear"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Chat channel cleared"


# async def test_chat_messages(bot: UnitTester, channel: TextChannel):
#   content = "!chat hey"
#   com = await channel.send(content)
#   assert com

#   msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
#   assert msg.content

async def test_chat_reset(bot: UnitTester, channel: TextChannel):
  content = "!reset"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "No history to delete" or msg.embeds[0].title == "My chat history has been reset"


async def test_persona(bot: UnitTester, channel: TextChannel):
  content = "!persona"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "This command requires a premium server and a patron or a mod."
