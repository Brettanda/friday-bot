import pytest
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from .conftest import bot, channel

pytestmark = pytest.mark.asyncio


async def test_prefix(bot: "bot", channel: "channel"):
  content = "!prefix ?"
  await channel.send(content)

  f_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)

  content = "?prefix !"
  assert await channel.send(content)
  l_msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert f_msg.embeds[0].title == "My new prefix is `?`" and l_msg.embeds[0].title == "My new prefix is `!`"


@pytest.mark.dependency(name="test_botchannel")
async def test_botchannel(bot: "bot", channel: "channel"):
  content = "!botchannel 892840236781015120"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Bot Channel"


@pytest.mark.dependency(depends=["test_botchannel"])
async def test_botchannel_clear(bot: "bot", channel: "channel"):
  content = "!botchannel clear"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Bot channel cleared"


@pytest.mark.dependency(name="test_disable")
@pytest.mark.parametrize("args", ["ping", "serverinfo"])
async def test_disable(bot: "bot", channel: "channel", args: str):
  content = f"!disable {args}"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == f"**{args}** has been disabled."


async def test_disable_list(bot: "bot", channel: "channel"):
  content = "!disable list"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Disabled Commands"
  assert len(msg.embeds[0].description) > 0


@pytest.mark.dependency(depends=["test_disable"])
@pytest.mark.parametrize("args", ["ping", "serverinfo"])
async def test_enable(bot: "bot", channel: "channel", args: str):
  content = f"!enable {args}"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == f"**{args}** has been enabled."


@pytest.mark.dependency(name="test_restrict")
@pytest.mark.parametrize("args", ["ping", "serverinfo"])
async def test_restrict(bot: "bot", channel: "channel", args: str):
  content = f"!restrict {args}"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == f"**{args}** has been restricted to the bot channel."


async def test_restrict_list(bot: "bot", channel: "channel"):
  content = "!restrict list"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == "Restricted Commands"
  assert len(msg.embeds[0].description) > 0


@pytest.mark.dependency(depends=["test_restrict"])
@pytest.mark.parametrize("args", ["ping", "serverinfo"])
async def test_unrestrict(bot: "bot", channel: "channel", args: str):
  content = f"!unrestrict {args}"
  assert await channel.send(content)

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, content=content), timeout=pytest.timeout)
  assert msg.embeds[0].title == f"**{args}** has been unrestricted."
