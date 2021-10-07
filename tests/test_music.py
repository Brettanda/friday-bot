import discord
import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, voice_channel, channel


# @pytest.mark.parametrize("bot,voice_channel,channel", [bot, voice_channel, channel])
@pytest.mark.asyncio
@pytest.mark.dependency()
async def test_play(bot: "bot", voice_channel: "voice_channel", channel: "channel"):
  await voice_channel.connect()
  content = "!p https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Now playing: **Rick Astley - Never Gonna Give You Up (Official Music Video)**"


@pytest.mark.asyncio
@pytest.mark.dependency(depends=["test_play"])
async def test_more_for_queue(bot: "bot", voice_channel: "voice_channel", channel: "channel"):
  content = "!p https://www.youtube.com/watch?v=2ZIpFytCSVc"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Added to queue: **Bruh Sound Effect #2**"


@pytest.mark.asyncio
@pytest.mark.dependency(depends=["test_play", "test_more_for_queue"])
async def test_queue(bot: "bot", voice_channel: "voice_channel", channel: "channel"):
  content = "!queue"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "Now playing:" in msg.embeds[0].title and "Up Next:" in msg.embeds[0].description


@pytest.mark.asyncio
@pytest.mark.dependency(depends=["test_play"])
async def test_stop(bot: "bot", channel: "channel"):
  content = "!stop"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Finished"


class TestCustomSounds:
  @pytest.mark.asyncio
  async def test_custom(self, bot: "bot", channel: "channel"):
    content = "!c"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "You're missing some arguments, here is how the command should look"

  @pytest.mark.asyncio
  @pytest.mark.dependency()
  async def test_add(self, bot: "bot", channel: "channel"):
    content = "!c add bruh https://www.youtube.com/watch?v=2ZIpFytCSVc"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "I will now play `https://www.youtube.com/watch?v=2ZIpFytCSVc` for the command `!custom bruh`"

  @pytest.mark.asyncio
  @pytest.mark.dependency(depends=["test_add"], scope="class")
  async def test_play_bruh(self, bot: "bot", voice_channel: "voice_channel", channel: "channel"):
    try:
      vc = await voice_channel.connect()
    except discord.ClientException:
      pass
    content = "!c bruh"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    try:
      await vc.disconnect()
    except Exception:
      pass
    assert msg.embeds[0].title == "Now playing: **Bruh Sound Effect #2**"

  @pytest.mark.asyncio
  async def test_list(self, bot: "bot", voice_channel: "voice_channel", channel: "channel"):
    content = "!c list"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "The list of custom sounds"

  @pytest.mark.asyncio
  async def test_remove(self, bot: "bot", channel: "channel"):
    content = "!c remove bruh"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "Removed the custom sound `bruh`" or msg.embeds[0].title == "Could not find the custom command"
