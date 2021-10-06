import pytest


@pytest.mark.asyncio
async def test_coinflip(bot, channel):
  await channel.send("!coinflip")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert "The coin landed on: " in msg.embeds[0].title


@pytest.mark.asyncio
async def test_souptime(bot, channel):
  await channel.send("!souptime")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert "Here is sum soup, just for you" in msg.embeds[0].title


@pytest.mark.asyncio
async def test_rockpaperscissors(bot, channel):
  await channel.send("!rps rock")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert "The winner of this round is:" in msg.embeds[0].description


@pytest.mark.asyncio
async def test_countdown(bot, channel):
  await channel.send("!countdown 0 0 20")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert msg.embeds[0].title == "Countdown:"


@pytest.mark.asyncio
async def test_poll(bot, channel):
  await channel.send("""!poll "this is a title" "yes" "no" """)

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  await bot.wait_for("raw_reaction_add", timeout=pytest.timeout)
  await bot.wait_for("raw_reaction_add", timeout=pytest.timeout)
  assert msg.embeds[0].title == "Poll: this is a title"


@pytest.mark.asyncio
async def test_minesweeper(bot, channel):
  await channel.send("!ms")

  def ms_check(m) -> bool:
    return m.channel.id == channel.id and m.author.id == 751680714948214855

  msg = await bot.wait_for("message", check=ms_check, timeout=pytest.timeout)
  assert msg.embeds[0].author.name == "Minesweeper"
