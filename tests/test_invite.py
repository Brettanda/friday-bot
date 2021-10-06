import pytest


@pytest.mark.asyncio
async def test_invite(bot, channel):
  await channel.send("!invite")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert msg.embeds[0].title == "Invite me :)"
