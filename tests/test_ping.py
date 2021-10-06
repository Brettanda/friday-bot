import pytest


@pytest.mark.asyncio
async def test_ping(bot, channel):
  await channel.send("!ping")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert msg.embeds[0].title == "Pong!"
