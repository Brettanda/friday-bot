from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from .conftest import send_command

if TYPE_CHECKING:
  from discord import TextChannel

  from .conftest import Friday, UnitTester, UnitTesterUser

pytestmark = pytest.mark.asyncio


@pytest.mark.dependency()
async def test_get_cog(friday: Friday):
  assert friday.get_cog("Dev") is not None


@pytest.mark.parametrize("command", ["dev reload", "dev", "dev say", "dev reload all"])
@pytest.mark.dependency(depends=["test_get_cog"])
async def test_dev(bot_user: UnitTesterUser, channel_user: TextChannel, command: str):
  content = f"!dev {command}"
  com = await channel_user.send(content)
  assert com

  with pytest.raises(asyncio.TimeoutError):
    await bot_user.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=2.0)  # type: ignore


@pytest.mark.parametrize("command", ["sudo 813618591878086707 dev", ])
@pytest.mark.dependency(depends=["test_get_cog"])
async def test_dev_with_sudo(bot: UnitTester, channel: TextChannel, command: str):
  content = f"!dev {command}"
  com = await send_command(bot, channel, content)

  with pytest.raises(asyncio.TimeoutError):
    await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=2.0)  # type: ignore
