from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("words", ["hey bruh", '"big bruh moment"', "welcome"])
async def test_say(bot: bot, channel: channel, words: str):
  content = f"!say {words}"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.content == words


async def test_say_no_argument(bot: bot, channel: channel):
  content = "!say"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "!say"


async def test_chatchannel(bot: bot, channel: channel):
  content = "!chatchannel"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Current chat channel"
  assert msg.embeds[0].description


async def test_chatchannel_set(bot: bot, channel: channel):
  content = "!chatchannel 892840236781015120"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Chat channel set"


async def test_chatchannel_voice_channel(bot: bot, channel: channel):
  content = "!chatchannel 895486009465266176"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Channel \"895486009465266176\" not found."


async def test_chatchannel_clear(bot: bot, channel: channel):
  content = "!chatchannel clear"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Chat channel cleared"


# async def test_chat_messages(bot: bot, channel: channel):
#   content = "!chat hey"
#   assert await channel.send(content)

#   msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
#   assert msg.content

async def test_chat_reset(bot: bot, channel: channel):
  content = "!reset"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "No history to delete" or msg.embeds[0].title == "My chat history has been reset"


async def test_persona(bot: bot, channel: channel):
  content = "!persona"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "This command requires a premium server and a patron or a mod."
