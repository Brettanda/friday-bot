import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel


@pytest.mark.asyncio
@pytest.mark.parametrize("words", ["hey bruh", '"big bruh moment"', "welcome"])
async def test_say(bot: "bot", channel: "channel", words: str):
  content = f"!say {words}"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.content == words


@pytest.mark.asyncio
async def test_say_no_argument(bot: "bot", channel: "channel"):
  content = "!say"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "!say"
