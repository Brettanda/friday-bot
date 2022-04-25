import asyncio
import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, bot_user, channel_user, channel

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("command", ["sudo 813618591878086707 dev reload", "sudo 813618591878086707 dev", "sudo 813618591878086707 dev say", "sudo 813618591878086707 dev reload all"])
async def test_dev(bot_user: "bot_user", channel_user: "channel_user", command: str):
  content = f"!dev {command}"
  assert await channel_user.send(content)

  with pytest.raises(asyncio.TimeoutError):
    await bot_user.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=2.0)


@pytest.mark.parametrize("command", ["sudo 813618591878086707 dev", ])
async def test_dev_with_sudo(bot: "bot", channel: "channel", command: str):
  content = f"!dev {command}"
  assert await channel.send(content)

  with pytest.raises(asyncio.TimeoutError):
    await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=2.0)
