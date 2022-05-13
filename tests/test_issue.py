from __future__ import annotations

from typing import TYPE_CHECKING
import pytest


if TYPE_CHECKING:
  from discord import TextChannel

  from .conftest import UnitTester

pytestmark = pytest.mark.asyncio


@pytest.mark.skip("Not implemented")
async def test_issue(bot: UnitTester, channel: TextChannel):
  ...
