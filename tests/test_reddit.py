from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from functions.messagecolors import MessageColors

from .conftest import send_command

if TYPE_CHECKING:
  from discord.channel import TextChannel

  from .conftest import Friday, UnitTester

pytestmark = pytest.mark.asyncio


@pytest.mark.dependency()
async def test_get_cog(friday: Friday):
  assert friday.get_cog("redditlink") is not None


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_text(bot: UnitTester, channel: TextChannel):
  content = "!redditextract https://www.reddit.com/r/GPT3/comments/q2gr84/how_to_get_multiple_outputs_from_the_same_prompt/"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout * 2.0)  # type: ignore
  assert msg.embeds[0].type == "image" or msg.embeds[0].color.value != MessageColors.error()


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_video(bot: UnitTester, channel: TextChannel):
  content = "!redditextract https://www.reddit.com/r/WinStupidPrizes/comments/q2o2p8/twerking_in_a_car_wash_with_the_door_open/"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout * 10.0)  # type: ignore
  assert len(msg.attachments) > 0
  assert "video/" in msg.attachments[0].content_type


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_image(bot: UnitTester, channel: TextChannel):
  content = "!redditextract https://www.reddit.com/r/woooosh/comments/q2hzu3/this_is_heartbreaking/"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout * 3.0)  # type: ignore
  assert msg.embeds[0].type == "image"
  if msg.embeds[0].color is not None:
    assert hasattr(msg.embeds[0].color, "value") and msg.embeds[0].color.value != MessageColors.error()


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_gif(bot: UnitTester, channel: TextChannel):
  content = "!redditextract https://reddit.com/r/wholesomememes/comments/pz75c7/dont_worry_mom_i_got_this/"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout * 3.0)  # type: ignore
  assert msg.embeds[0].type == "image"
  if msg.embeds[0].color is not None:
    assert hasattr(msg.embeds[0].color, "value") and msg.embeds[0].color.value != MessageColors.error()


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_delete_before_post(bot: UnitTester, friday: Friday, channel: TextChannel):
  content = "!redditextract https://reddit.com/r/wholesomememes/comments/pz75c7/dont_worry_mom_i_got_this/"
  com = await send_command(bot, channel, content)

  await com.delete()
  msg = await bot.wait_for("message", check=lambda m: m.author.id == friday.user.id, timeout=pytest.timeout * 3.0)  # type: ignore
  assert msg.embeds[0].type == "image"
  assert msg.reference is None
  if msg.embeds[0].color is not None:
    assert hasattr(msg.embeds[0].color, "value") and msg.embeds[0].color.value != MessageColors.error()

# https://www.reddit.com/r/IsTodayFridayThe13th/comments/uounpa/is_today_friday_the_13th/?utm_medium=android_app&utm_source=share
# https://www.reddit.com/r/deathgrips/comments/uxg2j5/我看過錄像/?utm_medium=android_app&utm_source=share
# add test for the above link
# test should fail
