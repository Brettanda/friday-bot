import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel


@pytest.mark.asyncio
async def test_coinflip(bot: "bot", channel: "channel"):
  content = "!coinflip"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "The coin landed on: " in msg.embeds[0].title


@pytest.mark.asyncio
async def test_souptime(bot: "bot", channel: "channel"):
  content = "!souptime"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert "Here is sum soup, just for you" in msg.embeds[0].title


@pytest.mark.asyncio
@pytest.mark.parametrize("choice", ["rock", "paper", "scissors", "", "asd"])
async def test_rockpaperscissors(bot: "bot", channel: "channel", choice):
  content = f"!rps {choice}"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  if choice == "asd":
    assert "`asd` is not Rock, Paper, Scissors. Please choose one of those three." in msg.embeds[0].title
  elif choice == "":
    assert "You're missing some arguments, here is how the command should look" in msg.embeds[0].title
  else:
    assert "The winner of this round is:" in msg.embeds[0].description


@pytest.mark.asyncio
async def test_countdown(bot: "bot", channel: "channel"):
  content = "!countdown 0 0 20"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Countdown:"


@pytest.mark.asyncio
async def test_poll(bot: "bot", channel: "channel"):
  content = '!poll "this is a title" "yes" "no"'
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  await bot.wait_for("raw_reaction_add", timeout=pytest.timeout)
  await bot.wait_for("raw_reaction_add", timeout=pytest.timeout)
  assert msg.embeds[0].title == "Poll: this is a title"


@pytest.mark.asyncio
async def test_minesweeper(bot: "bot", channel: "channel"):
  content = "!ms"
  await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].author.name == "Minesweeper"
