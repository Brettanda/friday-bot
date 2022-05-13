from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

from functions.messagecolors import MessageColors

if TYPE_CHECKING:
  from discord.channel import TextChannel

  from .conftest import UnitTester

pytestmark = pytest.mark.asyncio


async def test_text(bot: UnitTester, channel: TextChannel):
  content = "!redditextract https://www.reddit.com/r/GPT3/comments/q2gr84/how_to_get_multiple_outputs_from_the_same_prompt/"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout * 2.0)  # type: ignore
  assert msg.embeds[0].type == "image" or msg.embeds[0].color.value != MessageColors.error()


async def test_video(bot: UnitTester, channel: TextChannel):
  content = "!redditextract https://www.reddit.com/r/WinStupidPrizes/comments/q2o2p8/twerking_in_a_car_wash_with_the_door_open/"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout * 10.0)  # type: ignore
  assert len(msg.attachments) > 0
  assert "video/" in msg.attachments[0].content_type


async def test_image(bot: UnitTester, channel: TextChannel):
  content = "!redditextract https://www.reddit.com/r/woooosh/comments/q2hzu3/this_is_heartbreaking/"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout * 3.0)  # type: ignore
  assert msg.embeds[0].type == "image"
  if msg.embeds[0].color is not None:
    assert hasattr(msg.embeds[0].color, "value") and msg.embeds[0].color.value != MessageColors.error()


async def test_gif(bot: UnitTester, channel: TextChannel):
  content = "!redditextract https://reddit.com/r/wholesomememes/comments/pz75c7/dont_worry_mom_i_got_this/"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout * 3.0)  # type: ignore
  assert msg.embeds[0].type == "image"
  if msg.embeds[0].color is not None:
    assert hasattr(msg.embeds[0].color, "value") and msg.embeds[0].color.value != MessageColors.error()
