import asyncio
import pytest


@pytest.mark.asyncio
async def test_reload(bot, channel):
  await channel.send("!dev")

  with pytest.raises(asyncio.TimeoutError):
    await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout / 2)
