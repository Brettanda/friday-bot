import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel


@pytest.mark.asyncio
async def test_vote(bot: "bot", channel: "channel"):
  content = "!vote"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Voting"


@pytest.mark.asyncio
async def test_vote_remind(bot: "bot", channel: "channel"):
  content = "!vote remind"
  await channel.send(content)

  f_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  content = "!vote remind"
  await channel.send(content)
  l_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  options = ("I will now DM you every 12 hours after you vote for when you can vote again", "I will stop DMing you for voting reminders 😢")
  assert f_msg.embeds[0].title in options and l_msg.embeds[0].title in options
