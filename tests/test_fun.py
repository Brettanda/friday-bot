import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel

pytestmark = pytest.mark.asyncio


async def test_coinflip(bot: "bot", channel: "channel"):
  content = "!coinflip"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "The coin landed on: " in msg.embeds[0].title


async def test_souptime(bot: "bot", channel: "channel"):
  content = "!souptime"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "Here is sum soup, just for you" in msg.embeds[0].title


@pytest.mark.parametrize("choice", ["rock", "paper", "scissors", "", "asd"])
async def test_rockpaperscissors(bot: "bot", channel: "channel", choice):
  content = f"!rps {choice}"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  if choice == "asd":
    assert "`asd` is not Rock, Paper, Scissors. Please choose one of those three." in msg.embeds[0].title
  elif choice == "":
    assert "!rockpaperscissors" in msg.embeds[0].title
  else:
    assert "The winner of this round is:" in msg.embeds[0].description


async def test_poll(bot: "bot", channel: "channel"):
  content = '!poll "this is a title" "yes" "no"'
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  await bot.wait_for("raw_reaction_add", timeout=pytest.timeout)
  await bot.wait_for("raw_reaction_add", timeout=pytest.timeout)
  assert msg.embeds[0].title == "Poll: this is a title"


@pytest.mark.parametrize("size", range(2, 10))
@pytest.mark.parametrize("bombs", range(2, 15, 2))
async def test_minesweeper(bot: "bot", channel: "channel", size: int, bombs: int):
  content = f"!ms {size} {bombs}"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  if bombs >= size * size:
    assert msg.embeds[0].title == "Bomb count cannot be larger than the game board"
  else:
    assert msg.embeds[0].author.name == "Minesweeper"
    assert msg.embeds[0].title == f"{size or 5}x{size or 5} with {bombs or 6} bombs"
