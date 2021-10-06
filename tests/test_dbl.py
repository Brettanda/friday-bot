import pytest


@pytest.mark.asyncio
async def test_vote(bot, channel):
  await channel.send("!vote")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert msg.embeds[0].title == "Voting"


@pytest.mark.asyncio
async def test_vote_remind(bot, channel):
  await channel.send("!vote remind")

  f_msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  await channel.send("!vote remind")
  l_msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  options = ("I will now DM you every 12 hours after you vote for when you can vote again", "I will stop DMing you for voting reminders 😢")
  assert f_msg.embeds[0].title in options and l_msg.embeds[0].title in options
