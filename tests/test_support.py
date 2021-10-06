import pytest


@pytest.mark.asyncio
async def test_support(bot, channel):
  await channel.send("!support")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout / 2)
  assert msg.content == "https://discord.gg/NTRuFjU"


@pytest.mark.asyncio
async def test_donate(bot, channel):
  await channel.send("!donate")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout / 2)
  assert msg.content == "https://www.patreon.com/bePatron?u=42649008"
