from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

import discord
import pytest

from .conftest import send_command, msg_check

if TYPE_CHECKING:
  from discord import Guild
  from discord.channel import TextChannel, VoiceChannel

  from cogs.music import Music

  from .conftest import Friday, UnitTester, UnitTesterUser

pytestmark = pytest.mark.asyncio


async def music_is_working(friday: Friday, channel: TextChannel, guild_friday: Guild) -> bool:
  music_cog: Optional[Music] = friday.get_cog("Music")  # type: ignore
  assert music_cog is not None

  def check():
    player = music_cog.get_player(guild_friday)
    assert player is not None
    assert player.text_channel == channel
    assert player.dj == channel.guild.me
    assert player.ctx is not None
    assert player.bot is not None and player.bot == player.client
    assert player.source is not None and player.source == player.track
    assert player._paused is False
    assert player._connected is True
    for track in player.queue:
      assert track.title is not None
      assert track.requester == channel.guild.me
    return True

  assert check()
  await asyncio.sleep(10)
  assert check()

  player = music_cog.get_player(guild_friday)
  assert player is not None
  player.queue.reset()
  assert len(player.queue) == 0
  await player.stop()
  return True


@pytest.fixture(scope="module", autouse=True)
async def voice(bot: discord.Client, voice_channel: VoiceChannel, channel: TextChannel) -> discord.VoiceClient:  # type: ignore
  await bot.wait_until_ready()
  voice = voice_channel.guild.voice_client or await voice_channel.connect()
  yield voice
  await voice.disconnect(force=True)
  await channel.send("!stop")


@pytest.fixture(scope="module", autouse=True)
async def voice_user(bot_user: discord.Client, voice_channel_user: VoiceChannel, channel_user: TextChannel) -> discord.VoiceClient:  # type: ignore
  await bot_user.wait_until_ready()
  voice = voice_channel_user.guild.voice_client or await voice_channel_user.connect()
  yield voice
  await voice.disconnect(force=True)
  await channel_user.send("!stop")


# @pytest.mark.parametrize("bot,voice_channel,channel", [bot, voice_channel, channel])
@pytest.mark.parametrize("url", [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=OPf0YbXqDm0"])
async def test_play_youtube(bot: UnitTester, friday: Friday, channel: TextChannel, guild_friday: Guild, url: str):
  content = f"!p {url}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  # with pytest.raises(asyncio.TimeoutError):
  #   await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=2)  # type: ignore

  assert await music_is_working(friday, channel, guild_friday)
  assert "Now playing: **" in msg.embeds[0].title or "Added " in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title


async def test_play_spotify(bot: UnitTester, friday: Friday, channel: TextChannel, guild_friday: Guild):
  content = "!p https://open.spotify.com/track/0tyR7Bu9P086aWBFZ4QJoo?si=0f0ce5c3b5ee4b6b"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  # with pytest.raises(asyncio.TimeoutError):
  #   await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=2)  # type: ignore

  assert await music_is_working(friday, channel, guild_friday)
  assert "Now playing: **" in msg.embeds[0].title or "Added " in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title


async def test_play_spotify_playlist(bot: UnitTester, friday: Friday, channel: TextChannel, guild_friday: Guild):
  content = "!p https://open.spotify.com/playlist/2Z7q0uwOuJlpZ4CBeHXyeT?si=e400ddae1880457a"
  await send_command(bot, channel, content)

  await bot.wait_for("message", check=lambda message: message.author.id == friday.user.id, timeout=pytest.timeout * 2)  # type: ignore
  # with pytest.raises(asyncio.TimeoutError):
  #   await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=2)  # type: ignore

  assert await music_is_working(friday, channel, guild_friday)
  # assert "Now playing: **" in msg.embeds[0].title or "Added " in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title


async def test_play_spotify_album(bot: UnitTester, friday: Friday, channel: TextChannel, guild_friday: Guild):
  content = "!p https://open.spotify.com/album/5y2plpAX8NtK3q1Klatast?si=cea93f7a11224ae5"
  await send_command(bot, channel, content)

  await bot.wait_for("message", check=lambda message: message.author.id == friday.user.id, timeout=pytest.timeout * 2)  # type: ignore
  # with pytest.raises(asyncio.TimeoutError):
  #   await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=2)  # type: ignore

  assert await music_is_working(friday, channel, guild_friday)
  # assert "Now playing: **" in msg.embeds[0].title or "Added " in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title


@pytest.mark.dependency(name="test_play_playlist")
async def test_play_playlist(bot: UnitTester, friday: Friday, channel: TextChannel, guild_friday: Guild):
  content = "!p https://www.youtube.com/watch?v=jCQd6YqTnOk&list=PLQSoWXSpjA3_FFnFo4yWTtVbZrMkbm-h7"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  # with pytest.raises(asyncio.TimeoutError):
  #   await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=2)  # type: ignore

  assert await music_is_working(friday, channel, guild_friday)
  assert "Now playing: **" in msg.embeds[0].title or "Added " in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title


async def test_play_soundcloud(bot: UnitTester, friday: Friday, channel: TextChannel, guild_friday: Guild):
  content = "!p https://soundcloud.com/doughboyhen/anybodyk"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  # with pytest.raises(asyncio.TimeoutError):
  #   await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=2)  # type: ignore

  assert await music_is_working(friday, channel, guild_friday)
  assert "Now playing: **" in msg.embeds[0].title or "Added " in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title


async def test_play_not_url(bot: UnitTester, friday: Friday, channel: TextChannel, guild_friday: Guild):
  content = "!p some kind of magic"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  # with pytest.raises(asyncio.TimeoutError):
  #   await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=2)  # type: ignore

  assert await music_is_working(friday, channel, guild_friday)
  assert "Now playing: **" in msg.embeds[0].title or "Added " in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title


async def test_play_playlist_to_queue(bot: UnitTester, friday: Friday, channel: TextChannel, guild_friday: Guild):
  content = "!p https://www.youtube.com/watch?v=jCQd6YqTnOk&list=PLQSoWXSpjA3_FFnFo4yWTtVbZrMkbm-h7"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  # with pytest.raises(asyncio.TimeoutError):
  #   await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=2)  # type: ignore

  com = await send_command(bot, channel, content)

  msg2 = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  # with pytest.raises(asyncio.TimeoutError):
  #   await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=2)  # type: ignore

  assert await music_is_working(friday, channel, guild_friday)
  assert "Now playing: **" in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title
  assert "Added the playlist" in msg2.embeds[0].title


# # async def test_play_after_force_dc(bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
#   try:
#     await voice_channel.connect()
#   except discord.ClientException:
#     pass
#   content = "!p https://www.youtube.com/watch?v=dQw4w9WgXcQ"
#   com = await channel.send(content)
#   assert com

#   msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
#   assert "Now playing: **" in msg.embeds[0].title or "Added **" in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title

#   await msg.author.move_to(None)

#   content = "!p https://www.youtube.com/watch?v=dQw4w9WgXcQ"
#   com = await channel.send(content)
#   assert com

#   msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
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

#   msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
#   assert "Now playing: **" in msg.embeds[0].title or "Added **" in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title

#   await channel.send("!stop")

#   msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content="!stop"), timeout=pytest.timeout)
#   assert "stop" in msg.embeds[0].title or msg.embeds[0].title == "I am not playing anything."

#   content = "!p https://www.youtube.com/watch?v=dQw4w9WgXcQ"
#   com = await channel.send(content)
#   assert com

#   msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
#   assert "Now playing: **" in msg.embeds[0].title or "Added **" in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title

#   await channel.send("!stop")

#   msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content="!stop"), timeout=pytest.timeout)
#   assert "stop" in msg.embeds[0].title or msg.embeds[0].title == "I am not playing anything."


@pytest.mark.dependency(depends=["test_play_playlist"])
async def test_queue_no_songs(bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
  content = "!queue"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "There are no more songs in the queue." in msg.embeds[0].title


@pytest.mark.dependency(depends=["test_play_playlist"])
async def test_queue(bot: UnitTester, friday: Friday, guild_friday: Guild, voice_channel: VoiceChannel, channel: TextChannel):
  content = "!p https://www.youtube.com/watch?v=jCQd6YqTnOk&list=PLQSoWXSpjA3_FFnFo4yWTtVbZrMkbm-h7"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Now playing: **" in msg.embeds[0].title or "Added " in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title

  content = "!queue"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Coming up..." in msg.embeds[0].title or msg.embeds[0].title == "You must be in a voice channel or provide one to connect to."
  assert await music_is_working(friday, channel, guild_friday)


@pytest.mark.parametrize("vol", ["200", "100", "1"])
@pytest.mark.dependency(depends=["test_play_playlist"])
async def test_volume(bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel, vol: str):
  content = f"!volume {vol}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Set the volume to " in msg.embeds[0].title or "Please enter a value between 1 and 100." in msg.embeds[0].title


@pytest.mark.dependency(depends=["test_play_playlist"])
async def test_nowplaying_no_songs(bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
  content = "!nowplaying"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Nothing is playing right now." in msg.embeds[0].title


@pytest.mark.dependency(depends=["test_play_playlist"])
async def test_nowplaying(bot: UnitTester, friday: Friday, guild_friday: Guild, voice_channel: VoiceChannel, channel: TextChannel):
  content = "!p https://www.youtube.com/watch?v=jCQd6YqTnOk&list=PLQSoWXSpjA3_FFnFo4yWTtVbZrMkbm-h7"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Now playing: **" in msg.embeds[0].title or "Added " in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title

  content = "!nowplaying"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Now playing: **" in msg.embeds[0].title
  assert await music_is_working(friday, channel, guild_friday)


@pytest.mark.dependency(depends=["test_play_playlist"])
async def test_shuffle_no_songs(bot: UnitTester, friday: Friday, guild_friday: Guild, voice_channel: VoiceChannel, channel: TextChannel):
  content = "!p https://www.youtube.com/watch?v=jCQd6YqTnOk&list=PLQSoWXSpjA3_FFnFo4yWTtVbZrMkbm-h7"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Now playing: **" in msg.embeds[0].title or "Added " in msg.embeds[0].title or "Added the playlist" in msg.embeds[0].title
  assert await music_is_working(friday, channel, guild_friday)

  content = "!shuffle"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Add more songs to the queue before shuffling." in msg.embeds[0].title


async def test_shuffle(bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
  content = "!shuffle"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "An admin or DJ has shuffled the playlist." in msg.embeds[0].title or "Add more songs to the queue before shuffling." in msg.embeds[0].title


@pytest.mark.dependency(depends=["test_play_playlist"])
async def test_swap_dj(bot: UnitTester, bot_user: UnitTesterUser, guild_user: Guild, voice_channel: VoiceChannel, channel: TextChannel):
  content = f"!swap_dj {bot_user.user.id}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"{guild_user.me.display_name} is now the DJ."


@pytest.mark.dependency(depends=["test_play_playlist"])
async def test_equilizer(bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
  content = "!dev sudo 215227961048170496 eq flat"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "You do not have the required Patreon tier for this command." in msg.embeds[0].title or "Successfully changed equalizer to" in msg.embeds[0].title


@pytest.mark.dependency(depends=["test_play_playlist"])
async def test_stop(bot: UnitTester, channel: TextChannel):
  content = "!stop"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "stop" in msg.embeds[0].title or msg.embeds[0].title == "I am not playing anything."


class TestCustomSounds:
  async def test_custom(self, bot: UnitTester, channel: TextChannel):
    content = "!c"
    com = await send_command(bot, channel, content)

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == "The list of custom sounds" or "Now playing:" in msg.embeds[0].title or "Added" in msg.embeds[0].title or msg.embeds[0].title == "You must be in a voice channel to use this command"

  @pytest.mark.dependency(name="test_add", scope="class")
  @pytest.mark.parametrize("name,url", [["bruh", "https://www.youtube.com/watch?v=2ZIpFytCSVc"], ["rick", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"]])
  async def test_add(self, bot: UnitTester, channel: TextChannel, name: str, url: str):
    content = f"!c add {name} {url}"
    com = await send_command(bot, channel, content)

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == f"I will now play `{url}` for the command `!custom {name}`"

  @pytest.mark.dependency(depends=["test_add"], scope="class")
  async def test_play_bruh(self, bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
    content = "!c bruh"
    com = await send_command(bot, channel, content)

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert "Now playing: **" in msg.embeds[0].title

  async def test_list(self, bot: UnitTester, voice_channel: VoiceChannel, channel: TextChannel):
    content = "!c list"
    com = await send_command(bot, channel, content)

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == "The list of custom sounds"

  @pytest.mark.dependency(depends=["test_add"], scope="class")
  @pytest.mark.parametrize("name", ["bruh", "rick"])
  async def test_remove(self, bot: UnitTester, channel: TextChannel, name: str):
    content = f"!c remove {name}"
    com = await send_command(bot, channel, content)

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == f"Removed the custom sound `{name}`" or msg.embeds[0].title == "Could not find the custom command"

  @pytest.mark.depenency(depends=["test_add"], scope="class")
  async def test_clear(self, bot: UnitTester, channel: TextChannel):
    content = "!c clear"
    com = await send_command(bot, channel, content)

    msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == "Cleared this servers custom commands"
