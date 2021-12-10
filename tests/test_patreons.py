import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel


@pytest.mark.asyncio
async def test_patreon(bot: "bot", channel: "channel"):
  content = "!patreon"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout / 2)
  assert msg.embeds[0].title == "!patreon"


@pytest.mark.asyncio
async def test_server(bot: "bot", channel: "channel"):
  content = "!patreon server"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout / 2)
  assert msg.embeds[0].title == "You are not allowed to use this command"
