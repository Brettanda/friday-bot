from __future__ import annotations

import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel

pytestmark = pytest.mark.asyncio


class TestWelcome:
  async def test_welcome(self, bot: bot, channel: channel):
    content = "!welcome"
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert "Current Welcome Settings" == msg.embeds[0].title

  async def test_display(self, bot: bot, channel: channel):
    content = "!welcome display"
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert "Current Welcome Settings" in msg.embeds[0].title

  async def test_role(self, bot: bot, channel: channel):
    content = "!welcome role 895463648326221854"
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    content = "!welcome role"
    assert await channel.send(content)
    await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert "New members will now receive the role " in msg.embeds[0].title

  async def test_channel(self, bot: bot, channel: channel):
    content = f"!welcome channel {channel.id}"
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    content = "!welcome channel"
    assert await channel.send(content)
    await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert "Welcome message will be sent to" in msg.embeds[0].title

  @pytest.mark.parametrize("args", ["\"this is a message to {user} from {server}\"", ""])
  async def test_message(self, bot: bot, channel: channel, args: str):
    content = f'!welcome message {args}'
    assert await channel.send(content)

    msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
    assert msg.embeds[0].title == "This servers welcome message is now" or msg.embeds[0].title == "Welcome message removed"
