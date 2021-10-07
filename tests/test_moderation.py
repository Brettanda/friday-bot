import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, voice_channel, channel


@pytest.mark.asyncio
async def test_prefix(bot: "bot", channel: "channel"):
  content = "!prefix ?"
  await channel.send(content)

  f_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)

  content = "?prefix !"
  await channel.send(content)
  l_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert f_msg.embeds[0].title == "My new prefix is `?`" and l_msg.embeds[0].title == "My new prefix is `!`"


@pytest.mark.asyncio
async def test_lock(bot: "bot", voice_channel: "voice_channel", channel: "channel"):
  vc = await voice_channel.connect(timeout=10.0)
  content = "!lock 895486009465266176"
  await channel.send(content)

  f_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)

  await channel.send(content)
  l_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  await vc.disconnect()
  assert "Locked" in f_msg.embeds[0].title and "Unlocked" in l_msg.embeds[0].title


@pytest.mark.asyncio
async def test_language(bot: "bot", channel: "channel"):
  content = "!lang es"
  await channel.send(content)

  f_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  content = "!lang en"
  await channel.send(content)
  l_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert f_msg.embeds[0].title == "New language set to: `Spanish`" and l_msg.embeds[0].title == "New language set to: `English`"


class TestRemoveInvites:
  @pytest.mark.asyncio
  @pytest.mark.dependency()
  async def test_enable(self, bot: "bot", channel: "channel"):
    content = "!removeinvites 1"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "I will begin to remove invites"

  @pytest.mark.asyncio
  @pytest.mark.parametrize("content", ["https://discord.com/invite/NTRuFjU", "http://discord.com/invite/NTRuFjU", "https://discord.gg/NTRuFjU", "discord.com/invite/NTRuFjU", "discord.gg/NTRuFjU"])
  @pytest.mark.dependency(depends=["test_enable"], scope='class')
  async def test_external_guild(self, bot: "bot", channel: "channel", content: str):
    msg = await channel.send(content)

    msg = await bot.wait_for("raw_message_delete", check=lambda payload: pytest.raw_message_delete_check(payload, msg), timeout=pytest.timeout)
    assert msg.cached_message.content == content if msg.cached_message is not None else 1

  @pytest.mark.asyncio
  @pytest.mark.dependency(depends=["test_enable"], scope='class')
  async def test_xdisable(self, bot: "bot", channel: "channel"):
    content = "!removeinvites 0"
    await channel.send(content)

    l_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert l_msg.embeds[0].title == "I will no longer remove invites"


@pytest.mark.asyncio
async def test_deletecommandsafter(bot: "bot", channel: "channel"):
  content = "!deletecommandsafter 120"
  await channel.send(content)

  f_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert f_msg.embeds[0].title == "I will now delete commands after `120` seconds"
  content = "!deletecommandsafter"
  await channel.send(content)
  l_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert l_msg.embeds[0].title == "I will no longer delete command messages"


class TestBlacklist:
  @pytest.mark.asyncio
  @pytest.mark.dependency()
  async def test_add(self, bot, channel):
    content = "!blacklist add word"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "Added `word` to the blacklist" or msg.embeds[0].title == "Can't add duplicate word"

  @pytest.mark.asyncio
  @pytest.mark.dependency(depends=["test_add"], scope='class')
  async def test_add_another(self, bot, channel):
    content = "!blacklist add bad_word"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "Added `bad_word` to the blacklist" or msg.embeds[0].title == "Can't add duplicate word"

  @pytest.mark.asyncio
  @pytest.mark.dependency(depends=["test_add"], scope='class')
  async def test_remove(self, bot, channel):
    content = "!blacklist remove word"
    await channel.send(content)

    def say_check(m) -> bool:
      return m.channel.id == channel.id and m.author.id == 751680714948214855

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "Removed `word` from the blacklist" or msg.embeds[0].title == "You don't seem to be blacklisting that word"

  @pytest.mark.asyncio
  async def test_display(self, bot, channel):
    content = "!blacklist display"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "Blocked words" or msg.embeds[0].title == "No blacklisted words yet, use `!blacklist add <word>` to get started"

  @pytest.mark.asyncio
  @pytest.mark.dependency(depends=["test_add_another"], scope='class')
  async def test_clear(self, bot, channel):
    content = "!blacklist clear"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "Removed all blacklisted words"


class TestWelcome:
  @pytest.mark.asyncio
  async def test_welcome(self, bot, channel):
    content = "!welcome"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert "welcome" in msg.embeds[0].title

  @pytest.mark.asyncio
  async def test_display(self, bot, channel):
    content = "!welcome display"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert "Current Welcome Settings" in msg.embeds[0].title

  @pytest.mark.asyncio
  async def test_role(self, bot, channel):
    content = "!welcome role 895463648326221854"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    content = "!welcome role"
    await channel.send(content)
    await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert "New members will now receive the role " in msg.embeds[0].title

  @pytest.mark.asyncio
  async def test_channel(self, bot, channel):
    content = f"!welcome channel {channel.id}"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    content = "!welcome channel"
    await channel.send(content)
    await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert "Welcome message will be sent to" in msg.embeds[0].title

  @pytest.mark.asyncio
  async def test_message(self, bot, channel):
    content = '!welcome message "this is a message to {user} from {server}"'
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    content = "!welcome message"
    await channel.send(content)
    await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert "This servers welcome message is now" in msg.embeds[0].title and "this is a message to @Friday Unit Tester from Diary" in msg.embeds[0].description
