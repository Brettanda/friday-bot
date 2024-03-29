import discord
import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, voice_channel, channel


# @pytest.mark.parametrize("bot,voice_channel,channel", [bot, voice_channel, channel])
@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://www.youtube.com/watch?v=jCQd6YqTnOk&list=PLQSoWXSpjA3_FFnFo4yWTtVbZrMkbm-h7", "https://www.youtube.com/watch?v=2ZIpFytCSVc"])
@pytest.mark.dependency(name="test_play")
async def test_play(bot: "bot", voice_channel: "voice_channel", channel: "channel", url: str):
  try:
    await voice_channel.connect()
  except discord.ClientException:
    pass
  content = f"!p {url}"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "Now playing: **" in msg.embeds[0].title or "Added **" in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title


@pytest.mark.asyncio
@pytest.mark.dependency(depends=["test_play"])
async def test_queue(bot: "bot", voice_channel: "voice_channel", channel: "channel"):
  content = "!queue"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "Coming up..." in msg.embeds[0].title or msg.embeds[0].title == "You must be in a voice channel or provide one to connect to."


@pytest.mark.asyncio
@pytest.mark.parametrize("vol", ["200", "100", "1"])
@pytest.mark.dependency(depends=["test_play"])
async def test_volume(bot: "bot", voice_channel: "voice_channel", channel: "channel", vol: str):
  content = f"!volume {vol}"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "Set the volume to " in msg.embeds[0].title or "Please enter a value between 1 and 100." in msg.embeds[0].title


@pytest.mark.asyncio
@pytest.mark.dependency(depends=["test_play"])
async def test_nowplaying(bot: "bot", voice_channel: "voice_channel", channel: "channel"):
  content = "!nowplaying"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "Now playing: **" in msg.embeds[0].title


@pytest.mark.asyncio
@pytest.mark.dependency(depends=["test_play"])
async def test_shuffle(bot: "bot", voice_channel: "voice_channel", channel: "channel"):
  content = "!shuffle"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "An admin or DJ has shuffled the playlist." in msg.embeds[0].title


@pytest.mark.asyncio
@pytest.mark.dependency(depends=["test_play"])
async def test_equilizer(bot: "bot", voice_channel: "voice_channel", channel: "channel"):
  content = "!dev sudo 215227961048170496 eq flat"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "You do not have the required Patreon tier for this command." in msg.embeds[0].title or "Successfully changed equalizer to" in msg.embeds[0].title


@pytest.mark.asyncio
@pytest.mark.dependency(depends=["test_play"])
async def test_stop(bot: "bot", channel: "channel"):
  content = "!stop"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "stop" in msg.embeds[0].title or msg.embeds[0].title == "I am not playing anything."


class TestCustomSounds:
  @pytest.mark.asyncio
  async def test_custom(self, bot: "bot", channel: "channel"):
    content = "!c"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "!custom" or msg.embeds[0].title == "You must be in a voice channel to use this command"

  @pytest.mark.asyncio
  @pytest.mark.dependency(name="test_add", scope="class")
  @pytest.mark.parametrize("name,url", [["bruh", "https://www.youtube.com/watch?v=2ZIpFytCSVc"], ["rick", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]])
  async def test_add(self, bot: "bot", channel: "channel", name: str, url: str):
    content = f"!c add {name} {url}"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == f"I will now play `{url}` for the command `!custom {name}`"

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
    assert "Now playing: **" in msg.embeds[0].title

  @pytest.mark.asyncio
  async def test_list(self, bot: "bot", voice_channel: "voice_channel", channel: "channel"):
    content = "!c list"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "The list of custom sounds"

  @pytest.mark.asyncio
  @pytest.mark.dependency(depends=["test_add"], scope="class")
  @pytest.mark.parametrize("name", ["bruh", "rick"])
  async def test_remove(self, bot: "bot", channel: "channel", name: str):
    content = f"!c remove {name}"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == f"Removed the custom sound `{name}`" or msg.embeds[0].title == "Could not find the custom command"

  @pytest.mark.asyncio
  @pytest.mark.depenency(depends=["test_add"], scope="class")
  async def test_clear(self, bot: "bot", channel: "channel"):
    content = "!c clear"
    await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "Cleared this servers custom commands"
