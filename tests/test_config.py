from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from .conftest import send_command, msg_check

if TYPE_CHECKING:
  from discord import TextChannel

  from .conftest import Friday, UnitTester, UnitTesterUser

pytestmark = pytest.mark.asyncio


@pytest.mark.dependency()
async def test_get_cog(friday: Friday):
  assert friday.get_cog("Config") is not None


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_prefix(bot: UnitTester, channel: TextChannel):
  content = "!prefix ?"
  com = await send_command(bot, channel, content)

  f_msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore

  content = "?prefix !"
  com = await send_command(bot, channel, content)
  l_msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert f_msg.embeds[0].title == "My new prefix is `?`" and l_msg.embeds[0].title == "My new prefix is `!`"


async def test_language(bot: UnitTester, channel: TextChannel):
  content = "!lang es"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "New language set to: `Spanish`"

  content = "!lang polish"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "New language set to: `Polish`"

  content = "!lang en"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "New language set to: `English`"


@pytest.mark.dependency(name="test_botchannel")
@pytest.mark.dependency(depends=["test_get_cog"])
async def test_botchannel(bot: UnitTester, channel: TextChannel):
  content = "!botchannel 892840236781015120"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Bot Channel"


@pytest.mark.dependency(depends=["test_botchannel"])
@pytest.mark.dependency(depends=["test_get_cog"])
async def test_botchannel_clear(bot: UnitTester, channel: TextChannel):
  content = "!botchannel clear"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Bot channel cleared"


@pytest.mark.dependency(name="test_disable")
@pytest.mark.parametrize("args", ["ping", "serverinfo"])
@pytest.mark.dependency(depends=["test_get_cog"])
async def test_disable(bot: UnitTester, channel: TextChannel, args: str):
  content = f"!disable {args}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"**{args}** has been disabled."


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_disable_list(bot: UnitTester, channel: TextChannel):
  content = "!disable list"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Disabled Commands"
  assert len(msg.embeds[0].description) > 0


@pytest.mark.dependency(depends=["test_disable"])
@pytest.mark.parametrize("args", ["ping", "serverinfo"])
@pytest.mark.dependency(depends=["test_get_cog"])
async def test_enable(bot: UnitTester, channel: TextChannel, args: str):
  content = f"!enable {args}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"**{args}** has been enabled."


@pytest.mark.dependency(name="test_restrict")
@pytest.mark.parametrize("args", ["ping", "serverinfo"])
@pytest.mark.dependency(depends=["test_get_cog"])
async def test_restrict(bot: UnitTester, channel: TextChannel, args: str):
  content = f"!restrict {args}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"**{args}** has been restricted to the bot channel."


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_restrict_list(bot: UnitTester, channel: TextChannel):
  content = "!restrict list"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Restricted Commands"
  assert len(msg.embeds[0].description) > 0


@pytest.mark.dependency(depends=["test_restrict"])
@pytest.mark.parametrize("args", ["ping", "serverinfo"])
@pytest.mark.dependency(depends=["test_get_cog"])
async def test_unrestrict(bot: UnitTester, channel: TextChannel, args: str):
  content = f"!unrestrict {args}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"**{args}** has been unrestricted."


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_botchannel_restrict_commands(bot: UnitTester, bot_user: UnitTesterUser, channel: TextChannel, channel_user: TextChannel):
  other_channel = "824056692098072576"
  content = f"!botchannel {other_channel}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Bot Channel"
  assert other_channel in msg.embeds[0].description

  content = "!restrict ping"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "**ping** has been restricted to the bot channel."

  content = "!ping"
  com = await channel_user.send(content)
  assert com

  msg = await bot_user.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.content == f"<#{other_channel}>"
  assert msg.embeds[0].title == "This command is restricted to the bot channel."

  content = f"!botchannel {channel.id}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Bot Channel"
  assert channel.mention in msg.embeds[0].description

  content = "!ping"
  com = await channel_user.send(content)
  assert com

  msg = await bot_user.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Pong!"
  assert "API is" in msg.embeds[0].description
