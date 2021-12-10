import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel


@pytest.mark.asyncio
async def test_support(bot: "bot", channel: "channel"):
  content = "!support"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout / 2)
  assert msg.content == "https://discord.gg/NTRuFjU"


@pytest.mark.asyncio
async def test_donate(bot: "bot", channel: "channel"):
  content = "!donate"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout / 2)
  assert msg.content == "https://www.patreon.com/bePatron?u=42649008"
