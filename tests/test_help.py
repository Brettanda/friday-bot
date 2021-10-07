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
async def test_command_unknown(bot, channel):
  content = "!help asd"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == 'No command called "asd" found.'


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["ping", "souptime", "ban", "kick"])
async def test_command(bot, channel, command: str):
  content = f"!help {command}"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == f"!{command}"


@pytest.mark.asyncio
@pytest.mark.parametrize("cog", ["Music", "Moderation", "Dev", "TopGG"])
async def test_cog(bot, channel, cog: str):
  content = f"!help {cog}"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert cog in msg.embeds[0].title
  assert len(msg.embeds[0].fields) > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("group", ["blacklist", "custom", "welcome"])
async def test_group(bot: "bot", channel: "channel", group: str):
  content = f"!help {group}"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == f"!{group}"
  assert len(msg.embeds[0].fields) > 0


@pytest.mark.asyncio
@pytest.mark.parametrize("subcommand", ["blacklist add", "welcome role", "custom add"])
async def test_subcommand(bot: "bot", channel: "channel", subcommand: str):
  content = f"!help {subcommand}"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == f"!{subcommand}"
  assert len(msg.embeds[0].fields) > 0
