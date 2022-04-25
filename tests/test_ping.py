import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel

pytestmark = pytest.mark.asyncio


async def test_ping(bot: "bot", channel: "channel"):
  content = "!ping"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Pong!"
