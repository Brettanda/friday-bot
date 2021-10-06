import pytest
from functions.messagecolors import MessageColors


@pytest.mark.asyncio
async def test_bot(bot, channel):
  await channel.send("!info")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert "Friday" in msg.embeds[0].title and "- About" in msg.embeds[0].title and msg.embeds[0].color.value == MessageColors.DEFAULT


@pytest.mark.asyncio
async def test_user(bot, channel):
  await channel.send("!userinfo")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert msg.embeds[0].title == "Friday Unit Tester - Info"


@pytest.mark.asyncio
async def test_other_user(bot, channel):
  await channel.send("!userinfo 751680714948214855")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert "Friday" in msg.embeds[0].title and "- Info" in msg.embeds[0].title


@pytest.mark.asyncio
async def test_guild(bot, channel):
  await channel.send("!serverinfo")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert msg.embeds[0].title == f"{msg.guild.name if msg.guild is not None and msg.guild.name is not None else 'Diary'} - Info"
