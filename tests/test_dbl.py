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
