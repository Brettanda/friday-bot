from __future__ import annotations

import asyncio

import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import UnitTester, UnitTesterUser
  from discord import TextChannel

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("command", ["dev reload", "dev", "dev say", "dev reload all"])
async def test_dev(bot_user: UnitTesterUser, channel_user: TextChannel, command: str):
  content = f"!dev {command}"
  com = await channel_user.send(content)
  assert com

  with pytest.raises(asyncio.TimeoutError):
    await bot_user.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=2.0)  # type: ignore


@pytest.mark.parametrize("command", ["sudo 813618591878086707 dev", ])
async def test_dev_with_sudo(bot: UnitTester, channel: TextChannel, command: str):
  content = f"!dev {command}"
  com = await channel.send(content)
  assert com

  with pytest.raises(asyncio.TimeoutError):
    await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=2.0)  # type: ignore
