import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel


@pytest.mark.asyncio
async def test_help(bot: "bot", channel: "channel"):
  content = "!help"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Friday - Help"
  assert len(msg.embeds[0].fields) > 0


@pytest.mark.asyncio
async def test_command(bot, channel):
  content = "!help ping"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "!ping"
  assert msg.embeds[0].description == "Pong!"


@pytest.mark.asyncio
async def test_cog(bot, channel):
  content = "!help Music"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Music Commands"
  assert len(msg.embeds[0].fields) > 0


@pytest.mark.asyncio
async def test_group(bot: "bot", channel: "channel"):
  content = "!help blacklist"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "!blacklist"


@pytest.mark.asyncio
async def test_group_alias(bot: "bot", channel: "channel"):
  content = "!help bl"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "!blacklist"


@pytest.mark.asyncio
async def test_subcommand(bot: "bot", channel: "channel"):
  content = "!help blacklist add"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "!blacklist add"


@pytest.mark.asyncio
async def test_subcommand_alias(bot: "bot", channel: "channel"):
  content = "!help bl +"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "!blacklist add"
