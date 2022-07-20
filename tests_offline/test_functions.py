from __future__ import annotations

import pytest

from functions.config import PremiumPerks, PremiumTiersNew

pytestmark = pytest.mark.asyncio


async def test_premium_perks():
  perks = PremiumPerks()
  assert perks.tier == PremiumTiersNew.free
  assert perks.chat_ratelimit
  assert perks.guild_role is None
  assert perks.max_chat_channels == 1
  assert perks.max_chat_tokens == 25
  assert perks.max_chat_characters == 100
  assert perks.max_chat_history == 3

  perks = PremiumPerks(PremiumTiersNew.voted)
  assert perks.tier == PremiumTiersNew.voted
  assert perks.chat_ratelimit
  assert perks.guild_role is None
  assert perks.max_chat_channels == 1
  assert perks.max_chat_tokens == 25
  assert perks.max_chat_characters == 200
  assert perks.max_chat_history == 3

  perks = PremiumPerks(PremiumTiersNew.streaked)
  assert perks.tier == PremiumTiersNew.streaked
  assert perks.chat_ratelimit
  assert perks.guild_role is None
  assert perks.max_chat_channels == 1
  assert perks.max_chat_tokens == 25
  assert perks.max_chat_characters == 200
  assert perks.max_chat_history == 3

  perks = PremiumPerks(PremiumTiersNew.tier_1)
  assert perks.tier == PremiumTiersNew.tier_1
  assert perks.chat_ratelimit
  assert perks.guild_role is not None
  assert perks.max_chat_channels == 1
  assert perks.max_chat_tokens == 50
  assert perks.max_chat_characters == 200
  assert perks.max_chat_history == 5
