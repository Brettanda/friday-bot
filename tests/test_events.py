from __future__ import annotations

# import asyncio
import datetime
from typing import TYPE_CHECKING

import discord
import pytest

if TYPE_CHECKING:
  from discord import Guild

  from .conftest import Friday, UnitTester

pytestmark = pytest.mark.asyncio


@pytest.mark.dependency()
async def test_get_cog(friday: Friday):
  assert friday.get_cog("ScheduledEvents") is not None


@pytest.fixture(scope="module")
async def event(bot: UnitTester, guild: Guild) -> discord.ScheduledEvent:  # type: ignore
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


@pytest.fixture(scope="module")
async def role(bot: UnitTester, guild: Guild) -> discord.Role:  # type: ignore
  await bot.wait_until_ready()
  role = await guild.create_role(
      name="Test event role",
      reason="Testing"
  )
  yield role
  await role.delete()


# async def test_add_event_role(bot: UnitTester, channel: TextChannel, event: event, role: role):
#   content = f"!eventrole set {event.url} {role.id}"
#   com = await channel.send(content)
#   assert com
