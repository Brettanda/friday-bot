from __future__ import annotations

# import asyncio
import datetime
from typing import TYPE_CHECKING

import discord
import pytest

if TYPE_CHECKING:
  from .conftest import bot, guild

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="session")
async def event(bot: bot, guild: guild) -> discord.ScheduledEvent:
  await bot.wait_until_ready()
  event = await guild.create_scheduled_event(
      name="Test event",
      description="This is a test",
      entity_type=discord.EntityType.external,
      start_time=discord.utils.utcnow(),
      end_time=discord.utils.utcnow() + datetime.timedelta(hours=1),
      location="Test location",
      reason="Testing"
  )
  yield event
  await event.delete()


@pytest.fixture(scope="session")
async def role(bot: bot, guild: guild) -> discord.Role:
  await bot.wait_until_ready()
  role = await guild.create_role(
      name="Test event role",
      reason="Testing"
  )
  yield role
  await role.delete()


# async def test_add_event_role(bot: bot, channel: channel, event: event, role: role):
#   content = f"!eventrole set {event.url} {role.id}"
#   assert await channel.send(content)
