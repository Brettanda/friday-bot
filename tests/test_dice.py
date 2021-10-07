import pytest
from functions.messagecolors import MessageColors
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel


@pytest.mark.asyncio
async def test_dice(bot: "bot", channel: "channel"):
  content = "!dice 1d20"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "Your total:" in msg.embeds[0].title and msg.embeds[0].color.value == MessageColors.DEFAULT
