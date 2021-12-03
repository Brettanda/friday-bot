import asyncio
import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["sudo 813618591878086707 dev reload", "sudo 813618591878086707 dev", "sudo 813618591878086707 dev say", "sudo 813618591878086707 dev reload all"])
async def test_dev(bot: "bot", channel: "channel", command: str):
  content = f"!dev {command}"
  await channel.send(content)

  with pytest.raises(asyncio.TimeoutError):
    await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=2.0)


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["sudo 813618591878086707 dev", ])
async def test_dev_with_sudo(bot: "bot", channel: "channel", command: str):
  content = f"!dev {command}"
  await channel.send(content)

  with pytest.raises(asyncio.TimeoutError):
    await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=2.0)
