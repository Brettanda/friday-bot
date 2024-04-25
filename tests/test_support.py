from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from .conftest import send_command, msg_check

if TYPE_CHECKING:
  from discord.channel import TextChannel

  from .conftest import Friday, UnitTester

pytestmark = pytest.mark.asyncio


@pytest.mark.dependency()
async def test_get_cog(friday: Friday):
  assert friday.get_cog("Support") is not None


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_support(bot: UnitTester, channel: TextChannel):
  content = "!support"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout / 2)  # type: ignore
  assert msg.content == "https://discord.gg/NTRuFjU"


@pytest.mark.dependency(depends=["test_get_cog"])
async def test_donate(bot: UnitTester, channel: TextChannel):
  content = "!donate"
  com = await send_command(bot, channel, content)

  msg = await bot.wait_for("message", check=lambda message: msg_check(message, com), timeout=pytest.timeout / 2)  # type: ignore
  assert msg.content == "https://www.patreon.com/bePatron?u=42649008"
