from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

import pytest

from .conftest import send_command, msg_check

if TYPE_CHECKING:
  from discord import TextChannel, VoiceChannel

  from cogs.chat import Chat as ChatCog

  from .conftest import Friday, UnitTester

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True, scope="module")
async def get_cog(friday: Friday) -> ChatCog:
  await friday.wait_until_ready()
  cog: Optional[ChatCog] = friday.get_cog("Chat")  # type: ignore
  assert cog is not None
  return cog


@pytest.mark.parametrize("words", ["hey bruh", '"big bruh moment"', "welcome"])
async def test_say(bot: UnitTester, channel: TextChannel, words: str):
  content = f"!say {words}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.content == words


async def test_say_no_argument(bot: UnitTester, channel: TextChannel):
  content = "!say"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "!say"


async def test_chat(bot: UnitTester, friday: Friday, channel: TextChannel):
  assert friday.testing is True
  content = f"{friday.user.mention} hey how are you?"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.clean_content == "This message is a test"


async def test_chat_info(bot: UnitTester, channel: TextChannel):
  content = "!chat info"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Chat Info"
  assert len(msg.embeds[0].fields) == 6


async def test_chat_added_to_history(bot: UnitTester, friday: Friday, channel: TextChannel, get_cog: ChatCog):
  assert friday.testing is True
  content = "!reset"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "My chat history has been reset"

  content = f"{friday.user.mention} hey how are you?"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.clean_content == "This message is a test"

  chat_history = get_cog.chat_history[msg.channel.id]
  assert f"{bot.user.display_name}: @{friday.user.display_name} hey how are you?\n{friday.user.display_name}: This message is a test" in str(chat_history)


async def test_chat_command(bot: UnitTester, friday: Friday, channel: TextChannel):
  assert friday.testing is True
  content = "!chat hey how are you?"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.clean_content == "This message is a test"


async def test_chat_command_after_disabled(bot: UnitTester, friday: Friday, channel: TextChannel):
  assert friday.testing is True

  assert friday.get_cog("Config") is not None
  content = "!disable chat"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "**chat** has been disabled."

  content = f"{friday.user.mention} hey how are you?"
  com = await send_command(bot, channel, content)

  with pytest.raises(asyncio.TimeoutError):
    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.clean_content == "This message is a test"

  content = "!chat hey how are you?"
  com = await send_command(bot, channel, content)

  with pytest.raises(asyncio.TimeoutError):
    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.clean_content == "This message is a test"

  content = "!enable chat"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "**chat** has been enabled."


async def test_chatchannel(bot: UnitTester, channel: TextChannel):
  content = "!chatchannel"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Current chat channel"
  assert msg.embeds[0].description


@pytest.mark.dependency()
async def test_chatchannel_set(bot: UnitTester, channel: TextChannel):
  content = f"!chatchannel {channel.id}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Chat channel set"


@pytest.mark.dependency(depends=["test_chatchannel_set"])
async def test_chatchannel_chat(bot: UnitTester, channel: TextChannel):
  content = "hey how are you?"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.clean_content == "This message is a test"


async def test_chatchannel_voice_channel(bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
  content = f"!chatchannel {voice_channel.id}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"Channel \"{voice_channel.id}\" not found."


async def test_chatchannel_clear(bot: UnitTester, channel: TextChannel):
  content = "!chatchannel clear"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Chat channel cleared"


# @pytest.mark.dependency(depends=["test_get_cog"])
# async def test_chat_messages(bot: UnitTester, channel: TextChannel):
#   content = "!chat hey"
#   com = await channel.send(content)
#   assert com

#   msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
#   assert msg.content

async def test_chat_reset(bot: UnitTester, channel: TextChannel, get_cog: ChatCog):
  content = "!reset"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "No history to delete" or msg.embeds[0].title == "My chat history has been reset"

  chat_history = get_cog.chat_history[channel.id]
  assert len(chat_history.history()) == 0


async def test_persona(bot: UnitTester, channel: TextChannel):
  content = "!patreon server deactivate"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  # assert msg.embeds[0].title == "This command requires a premium server and a patron or a mod."

  content = "!persona"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "This command requires a premium server and a patron or a mod."
