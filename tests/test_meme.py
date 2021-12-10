import pytest
from functions.messagecolors import MessageColors
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel


@pytest.mark.asyncio
async def test_meme(bot: "bot", channel: "channel"):
  content = "!meme"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].color.value == MessageColors.MEME
