from __future__ import annotations

import discord
import pytest
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import UnitTester, UnitTesterUser


pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
async def voice(bot: discord.Client, voice_channel: discord.VoiceChannel, channel: discord.TextChannel) -> discord.VoiceClient:  # type: ignore
  await bot.wait_until_ready()
  voice = voice_channel.guild.voice_client or await voice_channel.connect()
  yield voice
  await voice.disconnect(force=True)
  await channel.send("!stop")


async def test_lock(bot: UnitTester, voice_channel: discord.VoiceChannel, channel: discord.TextChannel, voice: discord.VoiceClient):
  content = f"!lock {voice.channel.id}"
  com = await channel.send(content)
  assert com

  f_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert voice.channel.user_limit != 0
  com = await channel.send(content)
  assert com

  l_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert voice.channel.user_limit == 0
  assert "Locked" in f_msg.embeds[0].title and "Unlocked" in l_msg.embeds[0].title


async def test_language(bot: UnitTester, channel: discord.TextChannel):
  content = "!lang"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Select the language you would like me to speak in"


async def test_massmove(bot: UnitTester, channel: discord.TextChannel, voice_channel, voice: discord.VoiceClient):
  _id = 245688124108177411
  content = f"!move {_id}"
  com = await channel.send(content)
  assert com

  _, _, new_voice = await bot.wait_for("voice_state_update", check=lambda m, b, a: b.channel.id == voice.channel.id and a.channel.id == _id and b.channel != a.channel, timeout=pytest.timeout)  # type: ignore
  assert len(new_voice.channel.voice_states) > 0

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Successfully moved" in msg.embeds[0].title

  assert await channel.send(f"!move {voice_channel.id}")


@pytest.mark.dependency()
async def test_ban(bot: UnitTester, channel: discord.TextChannel):
  content = "!ban 969513051789361162 testing"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Banned Member ID 969513051789361162"


@pytest.mark.dependency(depends=["test_ban"])
async def test_unban(bot: UnitTester, channel: discord.TextChannel):
  content = "!unban <@969513051789361162>"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Unbanned" in msg.embeds[0].title


@pytest.mark.dependency()
async def test_hack_ban(bot: UnitTester, channel: discord.TextChannel):
  content = "!ban 969513051789361162 testing"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Banned Member ID 969513051789361162"


@pytest.mark.dependency(depends=["test_hack_ban"])
async def test_hack_unban(bot: UnitTester, channel: discord.TextChannel):
  content = "!unban 969513051789361162"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Unbanned" in msg.embeds[0].title


async def test_unban_fake(bot: UnitTester, channel: discord.TextChannel):
  content = "!unban 215227961048170496"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "This member has not been banned."


class TestMute:
  @pytest.mark.dependency()
  async def test_create_mute_role(self, bot: UnitTester, channel: discord.TextChannel, guild: discord.Guild):
    role = await guild.create_role(name="Test Mute Role", reason="Testing mute commands")
    assert role.name == "Test Mute Role"

    content = f"!mute role {role.id}"
    com = await channel.send(content)
    assert com

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert msg.embeds[0].title == f"Friday will now use `{role.name}` as the new mute role"

  @pytest.mark.dependency(depends=["test_create_mute_role"], scope="class")
  async def test_mute_role_update(self, bot: UnitTester, channel: discord.TextChannel):
    content = "!mute role update"
    com = await channel.send(content)
    assert com

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=30.0)  # type: ignore
    assert msg.embeds[0].title == "Mute role successfully updated"
    assert len(msg.embeds[0].description) > 10

  @pytest.mark.dependency()
  @pytest.mark.dependency(depends=["test_create_mute_role"], scope='class')
  async def test_mute(self, bot: UnitTester, bot_user: UnitTesterUser, channel: discord.TextChannel, guild_user: discord.Guild):
    content = f"!mute 1m {bot_user.user.id} test"
    com = await channel.send(content)
    assert com

    _, member = await bot_user.wait_for("member_update", check=lambda before, after: before.id == bot_user.user.id and before.roles != after.roles, timeout=pytest.timeout)  # type: ignore
    assert "Test Mute Role" in [r.name for r in member.roles]

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert f"Muted {bot_user.user.name}#{bot_user.user.discriminator} and retracted" in msg.embeds[0].title

  @pytest.mark.dependency(depends=["test_create_mute_role", "test_mute"], scope='class')
  async def test_unmute(self, bot: UnitTester, bot_user: UnitTesterUser, channel: discord.TextChannel, guild_user: discord.Guild):
    content = f"!unmute {bot_user.user.id} test"
    com = await channel.send(content)
    assert com

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
    assert "Test Mute Role" not in [r.name for r in guild_user.me.roles]
    assert msg.embeds[0].title == f"Unmuted {bot_user.user.name}#{bot_user.user.discriminator}"

  @pytest.mark.dependency(depends=["test_create_mute_role"], scope='class')
  async def test_mute_role_delete(self, bot: UnitTester, bot_user: UnitTesterUser, channel: discord.TextChannel, guild: discord.Guild):
    roles = await guild.fetch_roles()
    mute_roles = [r for r in roles if r.name == "Test Mute Role"]
    failed = 0
    for r in mute_roles:
      try:
        await r.delete(reason="Testing mute commands")
      except discord.HTTPException:
        failed += 1

    assert failed == 0
