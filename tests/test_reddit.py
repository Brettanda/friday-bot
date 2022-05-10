from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

from functions.messagecolors import MessageColors

if TYPE_CHECKING:
  from .conftest import bot, channel

pytestmark = pytest.mark.asyncio


async def test_text(bot: bot, channel: channel):
  content = "!redditextract https://www.reddit.com/r/GPT3/comments/q2gr84/how_to_get_multiple_outputs_from_the_same_prompt/"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout * 2.0)
  assert msg.embeds[0].type == "image" or msg.embeds[0].color.value != MessageColors.ERROR


async def test_video(bot: bot, channel: channel):
  content = "!redditextract https://www.reddit.com/r/WinStupidPrizes/comments/q2o2p8/twerking_in_a_car_wash_with_the_door_open/"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout * 10.0)
  assert len(msg.attachments) > 0
  assert "video/" in msg.attachments[0].content_type


async def test_image(bot: bot, channel: channel):
  content = "!redditextract https://www.reddit.com/r/woooosh/comments/q2hzu3/this_is_heartbreaking/"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout * 3.0)
  assert msg.embeds[0].type == "image"
  if msg.embeds[0].color is not None:
    assert hasattr(msg.embeds[0].color, "value") and msg.embeds[0].color.value != MessageColors.ERROR


async def test_gif(bot: bot, channel: channel):
  content = "!redditextract https://reddit.com/r/wholesomememes/comments/pz75c7/dont_worry_mom_i_got_this/"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout * 3.0)
  assert msg.embeds[0].type == "image"
  if msg.embeds[0].color is not None:
    assert hasattr(msg.embeds[0].color, "value") and msg.embeds[0].color.value != MessageColors.ERROR
