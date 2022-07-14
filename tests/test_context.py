from __future__ import annotations

from typing import TYPE_CHECKING

# import discord
import pytest

from functions import MyContext

# import asyncio

if TYPE_CHECKING:
  from discord import TextChannel

  from .conftest import Friday, UnitTester

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
async def context(friday: Friday, channel: TextChannel) -> MyContext:  # type: ignore
  await friday.wait_until_ready()
  content = "this is a message"
  message = await channel.send(content)
  assert message
  ctx = await friday.get_context(message, cls=MyContext)
  yield ctx

#   yield voice
#   await voice.disconnect()
#   await channel.send("!stop")


async def test_all_properties(friday: Friday, context: MyContext):
  ctx = context
  assert ctx.db is not None
  assert ctx.lang is not None
  assert ctx.guild is not None
  assert ctx.channel is not None
  assert ctx.author is not None
  assert ctx.message is not None
  assert hasattr(ctx, "prompt")
  assert hasattr(ctx, "get_lang")
  assert hasattr(ctx, "release")
  assert hasattr(ctx, "acquire")
  assert hasattr(ctx, "multi_select")
  assert hasattr(ctx, "safe_send")

# async def test_prompt(friday: friday, bot: UnitTester, context: context, channel: TextChannel):

#   asyncio.create_task(ctx.prompt("this is a prompt"))
#   msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout)  # type: ignore


async def test_delete_message_before_response(bot: UnitTester, friday: Friday, channel: TextChannel):
  content = "!ping"
  msg = await channel.send(content)
  assert msg

  await msg.delete()
  msg = await bot.wait_for("message", check=lambda m: m.embeds[0].title == "Pong!" and m.author.id == friday.user.id, timeout=pytest.timeout)  # type: ignore
  assert msg.reference is None
  assert "API is" in msg.embeds[0].description
