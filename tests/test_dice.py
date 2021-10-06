import pytest
from functions.messagecolors import MessageColors


@pytest.mark.asyncio
async def test_dice(bot, channel):
  await channel.send("!dice 1d20")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert "Your total:" in msg.embeds[0].title and msg.embeds[0].color.value == MessageColors.DEFAULT
