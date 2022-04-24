import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, voice_channel, channel

pytestmark = pytest.mark.asyncio


async def test_lock(bot: "bot", voice_channel: "voice_channel", channel: "channel"):
  vc = await voice_channel.connect(timeout=10.0)
  content = "!lock 895486009465266176"
  assert await channel.send(content)

  f_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)

  assert await channel.send(content)
  l_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  await vc.disconnect()
  assert "Locked" in f_msg.embeds[0].title and "Unlocked" in l_msg.embeds[0].title


async def test_language(bot: "bot", channel: "channel"):
  content = "!lang"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Select the language you would like me to speak in"


class TestRemoveInvites:
  @pytest.mark.dependency()
  async def test_enable(self, bot: "bot", channel: "channel"):
    content = "!removeinvites 1"
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "I will begin to remove invites"

  @pytest.mark.parametrize("content", ["https://discord.com/invite/NTRuFjU", "http://discord.com/invite/NTRuFjU", "https://discord.gg/NTRuFjU", "discord.com/invite/NTRuFjU", "discord.gg/NTRuFjU", "discord.gg/discord-developers"])
  @pytest.mark.dependency(depends=["test_enable"], scope='class')
  async def test_external_guild(self, bot: "bot", channel: "channel", content: str):
    msg = await channel.send(content)
    assert msg
    msg = await bot.wait_for("raw_message_delete", check=lambda payload: pytest.raw_message_delete_check(payload, msg), timeout=pytest.timeout)
    assert msg.cached_message.content == content if msg.cached_message is not None else 1

  @pytest.mark.dependency(depends=["test_enable"], scope='class')
  async def test_xdisable(self, bot: "bot", channel: "channel"):
    content = "!removeinvites 0"
    assert await channel.send(content)

    l_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert l_msg.embeds[0].title == "I will no longer remove invites"


class TestBlacklist:
  async def test_blacklist(self, bot, channel):
    content = "!blacklist"
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "Blocked words" or msg.embeds[0].title == "No blacklisted words yet, use `!blacklist add <word>` to get started"

  @pytest.mark.dependency()
  async def test_add(self, bot, channel):
    content = "!blacklist add word"
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "Added `word` to the blacklist" or msg.embeds[0].title == "Can't add duplicate word"

  @pytest.mark.dependency(depends=["test_add"], scope='class')
  async def test_add_another(self, bot, channel):
    content = "!blacklist add bad_word"
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "Added `bad_word` to the blacklist" or msg.embeds[0].title == "Can't add duplicate word"

  @pytest.mark.dependency(depends=["test_add"], scope='class')
  async def test_remove(self, bot, channel):
    content = "!blacklist remove word"
    assert await channel.send(content)

    def say_check(m) -> bool:
      return m.channel.id == channel.id and m.author.id == 751680714948214855

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "Removed `word` from the blacklist" or msg.embeds[0].title == "You don't seem to be blacklisting that word"

  async def test_display(self, bot, channel):
    content = "!blacklist display"
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "Blocked words" or msg.embeds[0].title == "No blacklisted words yet, use `!blacklist add <word>` to get started"

  @pytest.mark.dependency(depends=["test_add_another"], scope='class')
  async def test_clear(self, bot, channel):
    content = "!blacklist clear"
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "Removed all blacklisted words"


class TestWelcome:
  async def test_welcome(self, bot, channel):
    content = "!welcome"
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert "Current Welcome Settings" == msg.embeds[0].title

  async def test_display(self, bot, channel):
    content = "!welcome display"
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert "Current Welcome Settings" in msg.embeds[0].title

  async def test_role(self, bot, channel):
    content = "!welcome role 895463648326221854"
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    content = "!welcome role"
    assert await channel.send(content)
    await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert "New members will now receive the role " in msg.embeds[0].title

  async def test_channel(self, bot, channel):
    content = f"!welcome channel {channel.id}"
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    content = "!welcome channel"
    assert await channel.send(content)
    await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert "Welcome message will be sent to" in msg.embeds[0].title

  @pytest.mark.parametrize("args", ["\"this is a message to {user} from {server}\"", ""])
  async def test_message(self, bot, channel, args: str):
    content = f'!welcome message {args}'
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "This servers welcome message is now" or msg.embeds[0].title == "Welcome message removed"
