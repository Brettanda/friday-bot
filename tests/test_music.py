from __future__ import annotations

import discord
import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import UnitTester
  from discord.channel import TextChannel, VoiceChannel

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module", autouse=True)
async def voice(bot: discord.Client, voice_channel: VoiceChannel, channel: TextChannel) -> discord.VoiceClient:  # type: ignore
  await bot.wait_until_ready()
  voice = voice_channel.guild.voice_client or await voice_channel.connect()
  yield voice
  await voice.disconnect(force=True)
  await channel.send("!stop")


# @pytest.mark.parametrize("bot,voice_channel,channel", [bot, voice_channel, channel])
@pytest.mark.parametrize("url", ["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "https://www.youtube.com/watch?v=jCQd6YqTnOk&list=PLQSoWXSpjA3_FFnFo4yWTtVbZrMkbm-h7", "https://www.youtube.com/watch?v=2ZIpFytCSVc", "some kind of magic", "https://open.spotify.com/track/0tyR7Bu9P086aWBFZ4QJoo?si=0f0ce5c3b5ee4b6b", "https://open.spotify.com/playlist/2Z7q0uwOuJlpZ4CBeHXyeT?si=e400ddae1880457a"])
@pytest.mark.dependency(name="test_play")
async def test_play(bot: UnitTester, channel: TextChannel, url: str):
  content = f"!p {url}"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Now playing: **" in msg.embeds[0].title or "Added " in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title


# # async def test_play_after_force_dc(bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
#   try:
#     await voice_channel.connect()
#   except discord.ClientException:
#     pass
#   content = "!p https://www.youtube.com/watch?v=dQw4w9WgXcQ"
#   com = await channel.send(content)
#   assert com

#   msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
#   assert "Now playing: **" in msg.embeds[0].title or "Added **" in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title

#   await msg.author.move_to(None)

#   content = "!p https://www.youtube.com/watch?v=dQw4w9WgXcQ"
#   com = await channel.send(content)
#   assert com

#   msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
#   assert "Now playing: **" in msg.embeds[0].title or "Added **" in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title

#   await channel.send("!stop")

#   msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content="!stop"), timeout=pytest.timeout)
#   assert "stop" in msg.embeds[0].title or msg.embeds[0].title == "I am not playing anything."


# # async def test_play_after_stop(bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
#   try:
#     await voice_channel.connect()
#   except discord.ClientException:
#     pass
#   content = "!p https://www.youtube.com/watch?v=dQw4w9WgXcQ"
#   com = await channel.send(content)
#   assert com

#   msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
#   assert "Now playing: **" in msg.embeds[0].title or "Added **" in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title

#   await channel.send("!stop")

#   msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content="!stop"), timeout=pytest.timeout)
#   assert "stop" in msg.embeds[0].title or msg.embeds[0].title == "I am not playing anything."

#   content = "!p https://www.youtube.com/watch?v=dQw4w9WgXcQ"
#   com = await channel.send(content)
#   assert com

#   msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
#   assert "Now playing: **" in msg.embeds[0].title or "Added **" in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title

#   await channel.send("!stop")

#   msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content="!stop"), timeout=pytest.timeout)
#   assert "stop" in msg.embeds[0].title or msg.embeds[0].title == "I am not playing anything."


@pytest.mark.dependency(depends=["test_play"])
async def test_queue(bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
  content = "!queue"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Coming up..." in msg.embeds[0].title or msg.embeds[0].title == "You must be in a voice channel or provide one to connect to."


@pytest.mark.parametrize("vol", ["200", "100", "1"])
@pytest.mark.dependency(depends=["test_play"])
async def test_volume(bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel, vol: str):
  content = f"!volume {vol}"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Set the volume to " in msg.embeds[0].title or "Please enter a value between 1 and 100." in msg.embeds[0].title


@pytest.mark.dependency(depends=["test_play"])
async def test_nowplaying(bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
  content = "!nowplaying"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Now playing: **" in msg.embeds[0].title


@pytest.mark.dependency(depends=["test_play"])
async def test_shuffle(bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
  content = "!shuffle"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "An admin or DJ has shuffled the playlist." in msg.embeds[0].title


@pytest.mark.dependency(depends=["test_play"])
async def test_equilizer(bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
  content = "!dev sudo 215227961048170496 eq flat"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "You do not have the required Patreon tier for this command." in msg.embeds[0].title or "Successfully changed equalizer to" in msg.embeds[0].title


@pytest.mark.dependency(depends=["test_play"])
async def test_stop(bot: UnitTester, channel: TextChannel):
  content = "!stop"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "stop" in msg.embeds[0].title or msg.embeds[0].title == "I am not playing anything."


class TestCustomSounds:
  async def test_custom(self, bot: UnitTester, channel: TextChannel):
    content = "!c"
    com = await channel.send(content)
    assert com

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == "The list of custom sounds" or "Now playing:" in msg.embeds[0].title or "Added" in msg.embeds[0].title or msg.embeds[0].title == "You must be in a voice channel to use this command"

  @pytest.mark.dependency(name="test_add", scope="class")
  @pytest.mark.parametrize("name,url", [["bruh", "https://www.youtube.com/watch?v=2ZIpFytCSVc"], ["rick", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]])
  async def test_add(self, bot: UnitTester, channel: TextChannel, name: str, url: str):
    content = f"!c add {name} {url}"
    com = await channel.send(content)
    assert com

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == f"I will now play `{url}` for the command `!custom {name}`"

  @pytest.mark.dependency(depends=["test_add"], scope="class")
  async def test_play_bruh(self, bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
    content = "!c bruh"
    com = await channel.send(content)
    assert com

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert "Now playing: **" in msg.embeds[0].title

  async def test_list(self, bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
    content = "!c list"
    com = await channel.send(content)
    assert com

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == "The list of custom sounds"

  @pytest.mark.dependency(depends=["test_add"], scope="class")
  @pytest.mark.parametrize("name", ["bruh", "rick"])
  async def test_remove(self, bot: UnitTester, channel: TextChannel, name: str):
    content = f"!c remove {name}"
    com = await channel.send(content)
    assert com

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == f"Removed the custom sound `{name}`" or msg.embeds[0].title == "Could not find the custom command"

  @pytest.mark.depenency(depends=["test_add"], scope="class")
  async def test_clear(self, bot: UnitTester, channel: TextChannel):
    content = "!c clear"
    com = await channel.send(content)
    assert com

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == "Cleared this servers custom commands"
