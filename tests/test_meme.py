import pytest
from functions.messagecolors import MessageColors


@pytest.mark.asyncio
async def test_meme(bot, channel):
  await channel.send("!meme")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert msg.embeds[0].color.value == MessageColors.MEME
