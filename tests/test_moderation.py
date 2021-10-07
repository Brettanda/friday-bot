import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel


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
async def test_lock(bot, voice_channel, channel):
  await voice_channel.connect(timeout=10.0)
  content = "!lock 895486009465266176"
  await channel.send(content)

  f_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)

  await channel.send(content)
  l_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
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


class TestBlacklist:
  @pytest.mark.asyncio
  async def test_add(self, bot, channel):
    content = "!blacklist add word"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "Added `word` to the blacklist" or msg.embeds[0].title == "Can't add duplicate word"

  @pytest.mark.asyncio
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
    assert "This servers welcome message is now" in msg.embeds[0].title
