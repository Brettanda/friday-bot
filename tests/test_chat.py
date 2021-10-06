import pytest


@pytest.mark.asyncio
async def test_say(bot, channel):
  await channel.send("!say hey bruh")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout / 2)
  assert msg.content == "hey bruh"
