import pytest


@pytest.mark.asyncio
async def test_help(bot, channel):
  await channel.send("!help")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert msg.embeds[0].title == "Friday - Help" and len(msg.embeds[0].fields) > 1

# @pytest.mark.asyncio
# async def test_command(self, bot, channel):
#   await channel.send("!help ping")

#   msg = await bot.wait_for("message", check=pytest.msg_check, timeout=timeout)
#   assert msg.embeds[0].title == "Friday - Help" and len(msg.embeds[0].fields) > 1


@pytest.mark.asyncio
async def test_from_group(bot, channel):
  await channel.send("!patreon")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout)
  assert msg.embeds[0].title == "Help with `patreon`"
