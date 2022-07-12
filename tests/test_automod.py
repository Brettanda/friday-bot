from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

import pytest

from .conftest import send_command, msg_check

if TYPE_CHECKING:
  from discord import TextChannel

  from .conftest import Friday, UnitTester, UnitTesterUser
  from cogs.automod import AutoMod

pytestmark = pytest.mark.asyncio


async def test_message_spam(bot: UnitTester, bot_user: UnitTesterUser, friday: Friday, channel: TextChannel, channel_user: TextChannel):
  content = "!messagespam 3 5"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "I will now apply `mute` to messages matching the same author that are sent more than the rate of `3 messages`, for every `5 seconds`."

  automod: Optional[AutoMod] = friday.get_cog("AutoMod")  # type: ignore
  assert automod is not None

  with pytest.raises(KeyError):
    automod._spam_check[channel.guild.id]

  content = "hey"
  await channel_user.send(content)

  await asyncio.sleep(2)

  spam = automod._spam_check[channel.guild.id]
  assert spam is not None
  assert spam._message_spam is not None
  assert spam._message_spam != str(spam._mention_spam)

  content = "!messagespam disable"
  await send_command(bot, channel, content)


async def test_content_spam(bot: UnitTester, bot_user: UnitTesterUser, friday: Friday, channel: TextChannel, channel_user: TextChannel):
  content = "!contentspam 3 5"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "I will now apply `mute` to messages matching the same content that are sent more than the rate of `3 messages`, for every `5 seconds`."

  automod: Optional[AutoMod] = friday.get_cog("AutoMod")  # type: ignore
  assert automod is not None

  with pytest.raises(KeyError):
    automod._spam_check[channel.guild.id]

  content = "hey"
  await channel_user.send(content)

  await asyncio.sleep(2)

  spam = automod._spam_check[channel.guild.id]
  assert spam is not None
  assert spam._content_spam is not None
  assert spam._content_spam != str(spam._content_spam)

  content = "!contentspam disable"
  com = await send_command(bot, channel, content)
  await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore


async def test_mention_spam(bot: UnitTester, bot_user: UnitTesterUser, friday: Friday, channel: TextChannel, channel_user: TextChannel):
  content = "!mentionspam 3 5"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "I will now apply the punishments `mute` to members that mention `>=3` within `5 seconds`."

  automod: Optional[AutoMod] = friday.get_cog("AutoMod")  # type: ignore
  assert automod is not None

  with pytest.raises(KeyError):
    automod._spam_check[channel.guild.id]

  content = "hey"
  await channel_user.send(content)

  await asyncio.sleep(2)

  spam = automod._spam_check[channel.guild.id]
  assert spam is not None
  assert spam._mention_spam is not None
  assert spam._mention_spam != str(spam._mention_spam)

  content = "!mentionspam disable"
  com = await send_command(bot, channel, content)
  await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore


class TestRemoveInvites:
  @pytest.mark.dependency()
  async def test_enable(self, bot: UnitTester, channel: TextChannel):
    content = "!removeinvites 1"
    com = await send_command(bot, channel, content)

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == "I will begin to remove invites"

  @pytest.mark.parametrize("content", ["https://discord.com/invite/NTRuFjU", "http://discord.com/invite/NTRuFjU", "https://discord.gg/NTRuFjU", "discord.com/invite/NTRuFjU", "discord.gg/NTRuFjU", "discord.gg/discord-developers"])
  @pytest.mark.dependency(depends=["test_enable"], scope='class')
  async def test_external_guild(self, bot_user, channel_user, content: str):
    msg = await channel_user.send(content)
    assert msg
    msg = await bot_user.wait_for("raw_message_delete", check=lambda payload: pytest.raw_message_delete_check(payload, msg), timeout=pytest.timeout)  # type: ignore
    assert msg.cached_message.content == content if msg.cached_message is not None else 1

  @pytest.mark.parametrize("content", ["https://discord.com", "http://discord.com/moderator", "https://discord.gg", "discord.com", "discord.gg", "https://cdn.discordapp.com/attachments/737876653644054672/769247038684004382/unknown.png", "https://cdn.discordapp.com/attachments/599710801074323497/706438094647328778/unknown.png", "https://discord.com/application-directory/476303446547365891"])
  @pytest.mark.dependency(depends=["test_enable"], scope='class')
  async def test_not_guild(self, bot_user, channel_user, content: str):
    msg = await channel_user.send(content)
    assert msg

    with pytest.raises(asyncio.TimeoutError):
      msg = await bot_user.wait_for("raw_message_delete", check=lambda payload: pytest.raw_message_delete_check(payload, msg), timeout=pytest.timeout)  # type: ignore

  @pytest.mark.dependency(depends=["test_enable"], scope='class')
  async def test_xdisable(self, bot: UnitTester, channel: TextChannel):
    content = "!removeinvites 0"
    com = await send_command(bot, channel, content)

    l_msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert l_msg.embeds[0].title == "I will no longer remove invites"


class TestBlacklist:
  async def test_blacklist(self, bot: UnitTester, channel: TextChannel):
    content = "!blacklist"
    com = await send_command(bot, channel, content)

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == "Blocked words" or msg.embeds[0].title == "No blacklisted words yet, use `!blacklist add <word>` to get started"

  @pytest.mark.dependency(name="test_add", scope="class")
  @pytest.mark.parametrize("word", ["bad_word", "cum", "shit"])
  async def test_add(self, bot: UnitTester, channel: TextChannel, word: str):
    content = f"!blacklist add {word}"
    com = await send_command(bot, channel, content)

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == f"Added `{word}` to the blacklist" or msg.embeds[0].title == "Can't add duplicate word"

  @pytest.mark.dependency(depends=["test_add"], scope='class')
  async def test_add_existing(self, bot: UnitTester, channel: TextChannel):
    content = "!blacklist add bad_word"
    com = await send_command(bot, channel, content)

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == "Added badd_word to the blacklist"

    content = "!blacklist add bad_word"
    com = await send_command(bot, channel, content)

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == "Can't add duplicate word"

  @pytest.mark.dependency(depends=["test_add"], scope='class')
  @pytest.mark.parametrize("phrase", ["this message contains a bad_word", "cum", "shit", "s h i t", "thiscumasd", "c-u-m", "s-h-i-t"])
  async def test_words_get_removed(self, bot_user, channel_user: TextChannel, phrase: str):
    msg = await channel_user.send(phrase)
    assert msg

    # msg = await bot_user.wait_for("message_delete", check=lambda m: m.author.id == bot_user.user.id, timeout=pytest.timeout)
    msg = await bot_user.wait_for("raw_message_delete", check=lambda payload: pytest.raw_message_delete_check(payload, msg), timeout=pytest.timeout)  # type: ignore
    assert msg.cached_message.clean_content == phrase

  @pytest.mark.dependency(depends=["test_add"], scope='class')
  @pytest.mark.parametrize("phrase", ["this message contains", "ljakshd ljkahs ldj", " asjdlkjahslkdjhl", "a asd aasd ", "a-s-d-g-f-a-as"])
  async def test_words_dont_get_removed(self, bot_user, channel_user: TextChannel, phrase: str):
    msg = await channel_user.send(phrase)
    assert msg

    with pytest.raises(asyncio.TimeoutError):
      msg = await bot_user.wait_for("raw_message_delete", check=lambda payload: pytest.raw_message_delete_check(payload, msg), timeout=pytest.timeout)  # type: ignore

  @pytest.mark.dependency(depends=["test_add"], scope='class')
  async def test_remove(self, bot: UnitTester, channel: TextChannel):
    content = "!blacklist remove word"
    com = await send_command(bot, channel, content)

    def say_check(m) -> bool:
      return m.channel.id == channel.id and m.author.id == 751680714948214855

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == "Removed `word` from the blacklist" or msg.embeds[0].title == "You don't seem to be blacklisting that word"

  @pytest.mark.dependency(depends=["test_add"], scope='class')
  async def test_remove_nonexistent(self, bot: UnitTester, channel: TextChannel):
    content = "!blacklist remove kasjhdklj"
    com = await send_command(bot, channel, content)

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == "You don't seem to be blacklisting that word"

  async def test_display(self, bot: UnitTester, channel: TextChannel):
    content = "!blacklist display"
    com = await send_command(bot, channel, content)

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == "Blocked words" or msg.embeds[0].title == "No blacklisted words yet, use `!blacklist add <word>` to get started"

  @pytest.mark.dependency(depends=["test_add"], scope='class')
  async def test_clear(self, bot: UnitTester, channel: TextChannel):
    content = "!blacklist clear"
    com = await send_command(bot, channel, content)

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == "Removed all blacklisted words"
