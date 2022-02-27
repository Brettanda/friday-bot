import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel


@pytest.mark.asyncio
async def test_patreon(bot: "bot", channel: "channel"):
  content = "!patreon"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout / 2)
  assert msg.embeds[0].title == "Become a Patron!"


@pytest.mark.asyncio
async def test_server_activate(bot: "bot", channel: "channel"):
  content = "!patreon server activate"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout / 2)
  assert msg.embeds[0].title == "Your Patronage was not found"


@pytest.mark.asyncio
async def test_server_deactivate(bot: "bot", channel: "channel"):
  content = "!patreon server deactivate"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout / 2)
  assert msg.embeds[0].title == "This command requires a premium server and a patron or a mod."
