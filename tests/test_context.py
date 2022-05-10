from __future__ import annotations

from typing import TYPE_CHECKING

# import discord
import pytest

# import asyncio
from functions import MyContext

if TYPE_CHECKING:
  from .conftest import channel, friday

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
async def context(friday, channel: channel):
  await friday.wait_until_ready()
  content = "this is a message"
  message = await channel.send(content)
  assert message
  ctx = await friday.get_context(message, cls=MyContext)
  yield ctx

#   yield voice
#   await voice.disconnect()
#   await channel.send("!stop")


async def test_all_properties(friday: friday, context: context):
  ctx = context
  assert ctx.db
  assert ctx.guild
  assert ctx.channel
  assert ctx.author
  assert ctx.message

# async def test_prompt(friday: friday, bot: bot, context: context, channel: channel):

#   asyncio.create_task(ctx.prompt("this is a prompt"))
#   msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
