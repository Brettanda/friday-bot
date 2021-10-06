import pytest

from functions.messagecolors import MessageColors


@pytest.mark.asyncio
async def test_text(bot, channel):
  await channel.send("!redditextract https://www.reddit.com/r/GPT3/comments/q2gr84/how_to_get_multiple_outputs_from_the_same_prompt/")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout * 2)
  assert msg.embeds[0].type == "image" or msg.embeds[0].color.value != MessageColors.ERROR


@pytest.mark.asyncio
async def test_video(bot, channel):
  await channel.send("!redditextract https://www.reddit.com/r/WinStupidPrizes/comments/q2o2p8/twerking_in_a_car_wash_with_the_door_open/")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout * 10)
  assert len(msg.attachments) > 0 and "video/" in msg.attachments[0].content_type


@pytest.mark.asyncio
async def test_image(bot, channel):
  await channel.send("!redditextract https://www.reddit.com/r/woooosh/comments/q2hzu3/this_is_heartbreaking/")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout * 2)
  assert msg.embeds[0].type == "image" or (hasattr(msg.embeds[0].color, "value") and msg.embeds[0].color.value != MessageColors.ERROR)


@pytest.mark.asyncio
async def test_gif(bot, channel):
  await channel.send("!redditextract https://reddit.com/r/wholesomememes/comments/pz75c7/dont_worry_mom_i_got_this/")

  msg = await bot.wait_for("message", check=pytest.msg_check, timeout=pytest.timeout * 2)
  assert msg.embeds[0].type == "image" or (hasattr(msg.embeds[0].color, "value") and msg.embeds[0].color.value != MessageColors.ERROR)
