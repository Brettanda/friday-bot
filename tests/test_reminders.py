import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel


@pytest.mark.asyncio
async def test_reminders(bot: "bot", channel: "channel"):
  content = "!remind me in 5 minutes to do this"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "Reminder set" in msg.embeds[0].title


@pytest.mark.asyncio
async def test_reminders_list(bot: "bot", channel: "channel"):
  content = "!remind list"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Reminders"
