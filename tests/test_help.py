import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel


@pytest.mark.asyncio
async def test_help(bot: "bot", channel: "channel"):
  content = "!help"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Friday - Help" and len(msg.embeds[0].fields) > 1

# @pytest.mark.asyncio
# async def test_command(self, bot, channel):
#   content = "!help ping"
#   await channel.send(content)

#   msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=timeout)
#   assert msg.embeds[0].title == "Friday - Help" and len(msg.embeds[0].fields) > 1


@pytest.mark.asyncio
async def test_from_group(bot: "bot", channel: "channel"):
  content = "!patreon"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Help with `patreon`"
