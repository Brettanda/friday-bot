from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
  from discord import TextChannel

  from .conftest import Friday, UnitTester

pytestmark = pytest.mark.asyncio


@pytest.mark.dependency()
async def test_get_cog(friday: Friday):
  assert friday.get_cog("Issue") is not None


@pytest.mark.skip("Not implemented")
@pytest.mark.dependency(depends=["test_get_cog"])
async def test_issue(bot: UnitTester, channel: TextChannel):
  ...
