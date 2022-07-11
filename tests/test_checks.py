from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from functions.checks import (guild_is_min_tier, is_admin,
                              is_admin_and_min_tier, is_min_tier,
                              is_mod_and_min_tier, is_mod_or_guild_permissions,
                              is_supporter, is_supporter_or_voted,
                              user_is_min_tier)
from functions.config import PremiumTiersNew

from functions.exceptions import NotInSupportServer, RequiredTier

if TYPE_CHECKING:
  from discord.channel import TextChannel

  from functions.custom_contexts import GuildContext

  from .conftest import Friday, UnitTester

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
async def ctx(bot: UnitTester, friday: Friday, channel: TextChannel) -> GuildContext:
  content = "checks test"
  com = await channel.send(content)
  assert com

  ctx: GuildContext = await friday.get_context(com)  # type: ignore
  return ctx

# async def test_user_is_tier(bot: UnitTester, friday: Friday, channel: TextChannel):
#   content = "user_is_tier"
#   com = await channel.send(content)
#   assert com

#   ctx: GuildContext | MyContext = await friday.get_context(com)
#   assert await user_is_tier().predicate(ctx)


async def test_is_min_tier(bot: UnitTester, friday: Friday, user_friday, channel: TextChannel, ctx: GuildContext):
  assert await is_min_tier(PremiumTiersNew.free.value).predicate(ctx)
  with pytest.raises(NotInSupportServer):
    await is_min_tier(PremiumTiersNew.tier_1.value).predicate(ctx)
  with pytest.raises(NotInSupportServer):
    await is_min_tier(PremiumTiersNew.tier_2.value).predicate(ctx)
  with pytest.raises(NotInSupportServer):
    await is_min_tier(PremiumTiersNew.tier_3.value).predicate(ctx)
  ctx.author = user_friday
  assert await is_min_tier(PremiumTiersNew.free.value).predicate(ctx)
  assert await is_min_tier(PremiumTiersNew.tier_1.value).predicate(ctx)
  with pytest.raises(RequiredTier):
    assert await is_min_tier(PremiumTiersNew.tier_2.value).predicate(ctx)
  with pytest.raises(RequiredTier):
    assert await is_min_tier(PremiumTiersNew.tier_3.value).predicate(ctx)


async def test_guild_is_min_tier(bot: UnitTester, friday: Friday, channel: TextChannel, ctx: GuildContext):
  assert await guild_is_min_tier(PremiumTiersNew.free.value).predicate(ctx)
  assert await guild_is_min_tier(PremiumTiersNew.tier_1.value).predicate(ctx) is False


async def test_user_is_min_tier(bot: UnitTester, friday: Friday, channel: TextChannel, ctx: GuildContext):
  assert await user_is_min_tier(PremiumTiersNew.free.value).predicate(ctx)


async def test_is_admin_and_min_tier(bot: UnitTester, friday: Friday, channel: TextChannel, ctx: GuildContext):
  with pytest.raises(RequiredTier):
    assert await is_admin_and_min_tier().predicate(ctx)


async def test_is_mod_and_min_tier(bot: UnitTester, friday: Friday, channel: TextChannel, ctx: GuildContext):
  assert await is_mod_and_min_tier(tier=PremiumTiersNew.free.value).predicate(ctx)


async def test_is_supporter(bot: UnitTester, friday: Friday, channel: TextChannel, ctx: GuildContext):
  assert await is_supporter().predicate(ctx)


# async def test_user_is_supporter(bot: UnitTester, friday: Friday, channel: TextChannel, ctx: GuildContext):
#   assert await user_is_supporter().predicate(ctx)


async def test_is_supporter_or_voted(bot: UnitTester, friday: Friday, channel: TextChannel, ctx: GuildContext):
  assert await is_supporter_or_voted().predicate(ctx)


# async def test_user_voted(bot: UnitTester, friday: Friday, channel: TextChannel, ctx: GuildContext):
#   assert await user_voted().predicate(ctx)


async def test_is_admin(bot: UnitTester, friday: Friday, channel: TextChannel, ctx: GuildContext):
  assert await is_admin().predicate(ctx) is False


async def test_is_mod_or_guild_permissions(bot: UnitTester, friday: Friday, channel: TextChannel, ctx: GuildContext):
  assert await is_mod_or_guild_permissions().predicate(ctx)
