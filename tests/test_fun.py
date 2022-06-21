from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import numpy.random as random
import pytest
from async_timeout import timeout
from discord.ext.commands import BadArgument

from .conftest import send_command

if TYPE_CHECKING:
  from discord import TextChannel

  from cogs.fun import Fun

  from .conftest import Friday, UnitTester

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True, scope="module")
async def test_get_cog(friday: Friday):
  await friday.wait_until_ready()
  assert friday.get_cog("Fun") is not None
  return


async def test_coinflip(bot: UnitTester, channel: TextChannel):
  content = "!coinflip"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "The coin landed on: " in msg.embeds[0].title


async def test_souptime(bot: UnitTester, channel: TextChannel):
  content = "!souptime"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "Here is sum soup, just for you" in msg.embeds[0].title


@pytest.mark.parametrize("choice", ["rock", "paper", "scissors", "", "asd"])
async def test_rockpaperscissors(bot: UnitTester, channel: TextChannel, choice):
  content = f"!rps {choice}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  if choice == "asd":
    assert "`asd` is not Rock, Paper, Scissors. Please choose one of those three." in msg.embeds[0].title
  elif choice == "":
    assert "!rockpaperscissors" in msg.embeds[0].title
  else:
    assert "The winner of this round is:" in msg.embeds[0].description


async def test_poll(bot: UnitTester, channel: TextChannel):
  content = '!poll "this is a title" "yes" "no"'
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  await bot.wait_for("raw_reaction_add", timeout=pytest.timeout)  # type: ignore
  await bot.wait_for("raw_reaction_add", timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Poll: this is a title"
  assert "yes" in msg.embeds[0].fields[0].name
  assert "no" in msg.embeds[0].fields[1].name

  await msg.add_reaction("1️⃣")
  b_edited, a_edited = await bot.wait_for("message_edit", check=lambda b, a: b.embeds[0].title == "Poll: this is a title", timeout=15.0)
  assert "0% (0/0)" in b_edited.embeds[0].fields[0].value
  assert "0% (0/0)" in b_edited.embeds[0].fields[1].value
  assert "100% (1/1)" in a_edited.embeds[0].fields[0].value
  assert "0% (0/1)" in a_edited.embeds[0].fields[1].value


@pytest.mark.parametrize("size", range(0, 10))
@pytest.mark.parametrize("bombs", range(0, 20))
async def test_minesweeper(friday: Friday, size: int, bombs: int):
  fun: Optional[Fun] = friday.get_cog("Fun")  # type: ignore
  assert fun is not None

  async with timeout(0.01, loop=friday.loop):
    try:
      mines = await friday.loop.run_in_executor(None, fun.mine_sweeper, size, bombs)
    except BadArgument:
      assert True
    else:
      print(f"completed {size} {bombs}")
      assert mines.count("💥") <= bombs


@pytest.mark.parametrize("size", range(2, 10, 5))
@pytest.mark.parametrize("bombs", range(2, 15, 5))
async def test_minesweeper_command(bot: UnitTester, channel: TextChannel, size: int, bombs: int):
  content = f"!ms {size} {bombs}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  if bombs >= size * size:
    assert msg.embeds[0].title == "Bomb count cannot be larger than the game board"
  else:
    assert msg.embeds[0].author.name == "Minesweeper"
    assert msg.embeds[0].title == f"{size or 5}x{size or 5} with {bombs or 6} bombs"


async def test_8ball(bot: UnitTester, channel: TextChannel):
  content = "!8ball are you happy?"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert "🎱 | " in msg.embeds[0].title


@pytest.mark.parametrize("start", [*range(-2, 10, 4), 100000000000000000000, -100000000000000000000])
@pytest.mark.parametrize("end", [*range(-2, 10, 4), 100000000000000000000, -100000000000000000000])
async def test_rng(bot: UnitTester, channel: TextChannel, start: int, end: int):
  content = f"!rng {start} {end}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  if start > end:
    assert msg.embeds[0].title == "Start cannot be greater than end"
  else:
    try:
      random.randint(start, end)
    except ValueError as e:
      if str(e) == "high is out of bounds for int64":
        assert msg.embeds[0].title == "One or both of the numbers are too large"
      elif str(e) == "low is out of bounds for int64":
        assert msg.embeds[0].title == "One or both of the numbers are too small"
      else:
        assert msg.embeds[0].title == "(╯°□°）╯︵ ┻━┻"
    else:
      assert start <= int(msg.embeds[0].title) <= end


async def test_choice(bot: UnitTester, channel: TextChannel):
  choices = range(1, 10)
  content = f"!choice {', '.join(str(i) for i in choices)}"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert int(msg.embeds[0].title) in choices
