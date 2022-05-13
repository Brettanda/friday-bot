from __future__ import annotations

import discord
import datetime
import pytest
from typing import TYPE_CHECKING, AsyncIterator, Optional, List

if TYPE_CHECKING:
  from .conftest import UnitTester, Friday, UnitTesterUser
  from discord.channel import TextChannel
  from discord import Guild

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
async def logs(guild) -> List[discord.AuditLogEntry]:
  return [a async for a in guild.audit_logs(limit=10, oldest_first=False)]


@pytest.fixture(scope="module", autouse=True)
async def get_owner(bot: UnitTester, friday: Friday, bot_user: UnitTesterUser, guild: Guild, guild_friday: Guild, guild_user: Guild) -> None:
  await bot.wait_until_ready()
  await friday.wait_until_ready()
  await bot_user.wait_until_ready()

  _ = guild.get_member(215227961048170496) or await guild.fetch_member(215227961048170496)
  await friday.get_or_fetch_member(guild_friday, 215227961048170496)
  _ = guild_user.get_member(215227961048170496) or await guild_user.fetch_member(215227961048170496)


@pytest.fixture(scope="module", autouse=True)
async def setup_logging_channel(friday: Friday, bot: UnitTester, channel: TextChannel):
  await bot.wait_until_ready()
  await friday.wait_until_ready()

  content = f"!modlog {channel.id}"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == f"Mod log channel has been set to `{channel}`"

  yield

  content = "!modlog"
  com = await channel.send(content)
  assert com

  msg = await bot.wait_for("message", check=lambda message: pytest.msg_check(message, com), timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Mod log channel has been set to `None`"


# @pytest.fixture(scope="module")
# async def mute_role(bot: UnitTester, channel: TextChannel) -> discord.Role:
#   await bot.wait_until_ready()
#   content =

@pytest.mark.parametrize("reason", ["", "Auto-mute for spamming.", "big sus times", "lajks hdlkjahs lkjdhlaksjhdlkj ashlkdjhaslk"])
async def test_bans_from_automod(friday: Friday, logs: List[discord.AuditLogEntry], bot: UnitTester, guild_friday: Guild, guild: Guild, guild_user: Guild, channel: TextChannel, reason: str):
  async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
    for log in logs[1:limit]:
      if log.action == action and log.user == user:
        yield log
    oldest_log = logs[0]
    oldest_log.action = discord.AuditLogAction.ban
    oldest_log.reason = reason
    oldest_log._target_id = guild_user.me.id
    oldest_log.user = guild_friday.me
    oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
    yield oldest_log

  friday.dispatch("member_ban", guild=guild_user, member=guild_user.me, audit_logs=audit_logs)

  def check(m) -> bool:
    return m.author.id == friday.user.id

  msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Ban"
  assert guild_user.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_user.me.id})" in msg.embeds[0].description
  assert guild_friday.me and guild_friday.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_friday.me.id})" in msg.embeds[0].description
  if reason:
    assert reason in msg.embeds[0].description
  else:
    assert "No reason given" in msg.embeds[0].description


@pytest.mark.parametrize("reason", ["", "being stupid", "sus"])
async def test_bans_not_friday(friday: Friday, logs: List[discord.AuditLogEntry], bot: UnitTester, guild_friday: Guild, guild: Guild, guild_user: Guild, channel: TextChannel, reason: str):
  async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
    for log in logs[1:limit]:
      if log.action == action and log.user == user:
        yield log
    oldest_log = logs[0]
    oldest_log.action = discord.AuditLogAction.ban
    oldest_log.reason = reason
    oldest_log._target_id = guild_user.me.id
    oldest_log.user = guild_friday.owner
    oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
    yield oldest_log

  friday.dispatch("member_ban", guild=guild_user, member=guild_user.me, audit_logs=audit_logs)

  def check(m) -> bool:
    return m.author.id == friday.user.id

  msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Ban"
  assert guild_user.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_user.me.id})" in msg.embeds[0].description
  assert guild_friday.owner and guild_friday.owner.mention in msg.embeds[0].description
  assert f"(ID: {guild_friday.owner.id})" in msg.embeds[0].description
  if reason:
    assert reason in msg.embeds[0].description
  else:
    assert "No reason given" in msg.embeds[0].description


@pytest.mark.skip("Not implemented")
async def test_bans_from_commands(friday: Friday):
  # async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
  #   for log in logs[1:limit]:
  #     if log.action == action and log.user == user:
  #       yield log
  #   oldest_log = logs[0]
  #   oldest_log.action = discord.AuditLogAction.ban
  #   oldest_log.reason = guild_friday.owner and create_command_reason(guild_friday.owner, reason) or reason
  #   oldest_log.target = guild_user.me
  #   oldest_log.user = guild_friday.me
  #   oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
  #   yield oldest_log

  # friday.dispatch("member_ban", guild=guild_user, member=guild_user.me, audit_logs=audit_logs)

  # def check(m) -> bool:
  #   return m.author.id == friday.user.id

  # msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  # assert msg.embeds[0].title == "Ban"
  # assert guild_user.me.mention in msg.embeds[0].description
  # assert guild_friday.me and guild_friday.me.mention in msg.embeds[0].description
  # if reason:
  #   assert reason in msg.embeds[0].description
  # else:
  #   assert "No reason given" in msg.embeds[0].description
  ...


@pytest.mark.parametrize("reason", ["", "Auto-mute for spamming.", "big sus times", "lajks hdlkjahs lkjdhlaksjhdlkj ashlkdjhaslk"])
async def test_unbans_from_automod(friday: Friday, logs: List[discord.AuditLogEntry], bot: UnitTester, guild_friday: Guild, guild: Guild, guild_user: Guild, channel: TextChannel, reason: str):
  async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
    for log in logs[1:limit]:
      if log.action == action and log.user == user:
        yield log
    oldest_log = logs[0]
    oldest_log.action = discord.AuditLogAction.unban
    oldest_log.reason = reason
    oldest_log._target_id = guild_user.me.id
    oldest_log.user = guild_friday.me
    oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
    yield oldest_log

  friday.dispatch("member_unban", guild=guild_user, member=guild_user.me, audit_logs=audit_logs)

  def check(m) -> bool:
    return m.author.id == friday.user.id

  msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Unban"
  assert guild_user.me.mention in msg.embeds[0].description
  assert guild_friday.me and guild_friday.me.mention in msg.embeds[0].description
  if reason:
    assert reason in msg.embeds[0].description
  else:
    assert "No reason given" in msg.embeds[0].description


@pytest.mark.parametrize("reason", ["", "stopped being stupid", "not sus"])
async def test_unbans_not_friday(friday: Friday, logs: List[discord.AuditLogEntry], bot: UnitTester, guild_friday: Guild, guild: Guild, guild_user: Guild, channel: TextChannel, reason: str):
  async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
    for log in logs[1:limit]:
      if log.action == action and log.user == user:
        yield log
    oldest_log = logs[0]
    oldest_log.action = discord.AuditLogAction.unban
    oldest_log.reason = reason
    oldest_log._target_id = guild_user.me.id
    oldest_log.user = guild_friday.owner
    oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
    yield oldest_log

  friday.dispatch("member_unban", guild=guild_user, member=guild_user.me, audit_logs=audit_logs)

  def check(m) -> bool:
    return m.author.id == friday.user.id

  msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Unban"
  assert guild_user.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_user.me.id})" in msg.embeds[0].description
  assert guild_friday.owner and guild_friday.owner.mention in msg.embeds[0].description
  assert f"(ID: {guild_friday.owner.id})" in msg.embeds[0].description
  if reason:
    assert reason in msg.embeds[0].description
  else:
    assert "No reason given" in msg.embeds[0].description


@pytest.mark.skip("Not implemented")
async def test_unbans_from_commands(friday: Friday):
  # async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
  #   for log in logs[1:limit]:
  #     if log.action == action and log.user == user:
  #       yield log
  #   oldest_log = logs[0]
  #   oldest_log.action = discord.AuditLogAction.ban
  #   oldest_log.reason = guild_friday.owner and create_command_reason(guild_friday.owner, reason) or reason
  #   oldest_log.target = guild_user.me
  #   oldest_log.user = guild_friday.me
  #   oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
  #   yield oldest_log

  # friday.dispatch("member_ban", guild=guild_user, member=guild_user.me, audit_logs=audit_logs)

  # def check(m) -> bool:
  #   return m.author.id == friday.user.id

  # msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  # assert msg.embeds[0].title == "Ban"
  # assert guild_user.me.mention in msg.embeds[0].description
  # assert guild_friday.me and guild_friday.me.mention in msg.embeds[0].description
  # if reason:
  #   assert reason in msg.embeds[0].description
  # else:
  #   assert "No reason given" in msg.embeds[0].description
  ...


@pytest.mark.parametrize("reason", ["", "big sus times", "lajks hdlkjahs lkjdhlaksjhdlkj ashlkdjhaslk"])
async def test_kicks_from_automod(friday: Friday, logs: List[discord.AuditLogEntry], bot: UnitTester, guild_friday: Guild, guild: Guild, guild_user: Guild, channel: TextChannel, reason: str):
  async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
    for log in logs[1:limit]:
      if log.action == action and log.user == user:
        yield log
    oldest_log = logs[0]
    oldest_log.action = discord.AuditLogAction.kick
    oldest_log.reason = reason
    oldest_log._target_id = guild_user.me.id
    oldest_log.user = guild_friday.me
    oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
    yield oldest_log

  friday.dispatch("member_remove", member=guild_user.me, audit_logs=audit_logs)

  def check(m) -> bool:
    return m.author.id == friday.user.id

  msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Kick"
  assert guild_user.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_user.me.id})" in msg.embeds[0].description
  assert guild_friday.me and guild_friday.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_friday.me.id})" in msg.embeds[0].description
  if reason:
    assert reason in msg.embeds[0].description
  else:
    assert "No reason given" in msg.embeds[0].description


@pytest.mark.parametrize("reason", ["", "being stupid", "sus"])
async def test_kicks_not_friday(friday: Friday, logs: List[discord.AuditLogEntry], bot: UnitTester, guild_friday: Guild, guild: Guild, guild_user: Guild, channel: TextChannel, reason: str):
  async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
    for log in logs[1:limit]:
      if log.action == action and log.user == user:
        yield log
    oldest_log = logs[0]
    oldest_log.action = discord.AuditLogAction.kick
    oldest_log.reason = reason
    oldest_log._target_id = guild_user.me.id
    oldest_log.user = guild_friday.owner
    oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
    yield oldest_log

  friday.dispatch("member_remove", member=guild_user.me, audit_logs=audit_logs)

  def check(m) -> bool:
    return m.author.id == friday.user.id

  msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Kick"
  assert guild_user.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_user.me.id})" in msg.embeds[0].description
  assert guild_friday.owner and guild_friday.owner.mention in msg.embeds[0].description
  assert f"(ID: {guild_friday.owner.id})" in msg.embeds[0].description
  if reason:
    assert reason in msg.embeds[0].description
  else:
    assert "No reason given" in msg.embeds[0].description


@pytest.mark.skip("Not implemented")
async def test_kicks_from_commands(friday: Friday):
  ...


@pytest.mark.skip("Not implemented")
@pytest.mark.parametrize("reason", ["", "big sus times", "lajks hdlkjahs lkjdhlaksjhdlkj ashlkdjhaslk"])
async def test_mutes_from_automod(friday: Friday, logs: List[discord.AuditLogEntry], bot: UnitTester, guild_friday: Guild, guild: Guild, guild_user: Guild, channel: TextChannel, reason: str):
  ...

  async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
    for log in logs[1:limit]:
      if log.action == action and log.user == user:
        yield log
    oldest_log = logs[0]
    oldest_log.action = discord.AuditLogAction.member_role_update
    oldest_log.reason = reason
    oldest_log._target_id = guild_user.me.id
    oldest_log.user = guild_friday.me
    oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
    yield oldest_log

  # new_me = guild_user.me
  # new_me.roles.append(discord.Object(id=))

  friday.dispatch("member_update", before=guild_user.me, after=None, audit_logs=audit_logs)

  def check(m) -> bool:
    return m.author.id == friday.user.id

  msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Kick"
  assert guild_user.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_user.me.id})" in msg.embeds[0].description
  assert guild_friday.me and guild_friday.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_friday.me.id})" in msg.embeds[0].description
  if reason:
    assert reason in msg.embeds[0].description
  else:
    assert "No reason given" in msg.embeds[0].description


@pytest.mark.skip("Not implemented")
@pytest.mark.parametrize("reason", ["", "being stupid", "sus"])
async def test_mutes_not_friday(friday: Friday, logs: List[discord.AuditLogEntry], bot: UnitTester, guild_friday: Guild, guild: Guild, guild_user: Guild, channel: TextChannel, reason: str):
  ...

  async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
    for log in logs[1:limit]:
      if log.action == action and log.user == user:
        yield log
    oldest_log = logs[0]
    oldest_log.action = discord.AuditLogAction.member_role_update
    oldest_log.reason = reason
    oldest_log._target_id = guild_user.me.id
    oldest_log.user = guild_friday.owner
    oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
    yield oldest_log

  friday.dispatch("member_update", member=guild_user.me, audit_logs=audit_logs)

  def check(m) -> bool:
    return m.author.id == friday.user.id

  msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Kick"
  assert guild_user.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_user.me.id})" in msg.embeds[0].description
  assert guild_friday.owner and guild_friday.owner.mention in msg.embeds[0].description
  assert f"(ID: {guild_friday.owner.id})" in msg.embeds[0].description
  if reason:
    assert reason in msg.embeds[0].description
  else:
    assert "No reason given" in msg.embeds[0].description


@pytest.mark.skip("Not implemented")
async def test_mutes_from_commands(friday: Friday):
  ...


@pytest.mark.skip("Not implemented")
@pytest.mark.parametrize("reason", ["", "big sus times", "lajks hdlkjahs lkjdhlaksjhdlkj ashlkdjhaslk"])
async def test_unmutes_from_automod(friday: Friday, logs: List[discord.AuditLogEntry], bot: UnitTester, guild_friday: Guild, guild: Guild, guild_user: Guild, channel: TextChannel, reason: str):
  ...

  async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
    for log in logs[1:limit]:
      if log.action == action and log.user == user:
        yield log
    oldest_log = logs[0]
    oldest_log.action = discord.AuditLogAction.member_role_update
    oldest_log.reason = reason
    oldest_log._target_id = guild_user.me.id
    oldest_log.user = guild_friday.me
    oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
    yield oldest_log

  # new_me = guild_user.me
  # new_me.roles.append(discord.Object(id=))

  friday.dispatch("member_update", before=guild_user.me, after=None, audit_logs=audit_logs)

  def check(m) -> bool:
    return m.author.id == friday.user.id

  msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Kick"
  assert guild_user.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_user.me.id})" in msg.embeds[0].description
  assert guild_friday.me and guild_friday.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_friday.me.id})" in msg.embeds[0].description
  if reason:
    assert reason in msg.embeds[0].description
  else:
    assert "No reason given" in msg.embeds[0].description


@pytest.mark.skip("Not implemented")
@pytest.mark.parametrize("reason", ["", "being stupid", "sus"])
async def test_unmutes_not_friday(friday: Friday, logs: List[discord.AuditLogEntry], bot: UnitTester, guild_friday: Guild, guild: Guild, guild_user: Guild, channel: TextChannel, reason: str):
  ...

  async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
    for log in logs[1:limit]:
      if log.action == action and log.user == user:
        yield log
    oldest_log = logs[0]
    oldest_log.action = discord.AuditLogAction.member_role_update
    oldest_log.reason = reason
    oldest_log._target_id = guild_user.me.id
    oldest_log.user = guild_friday.owner
    oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
    yield oldest_log

  friday.dispatch("member_update", member=guild_user.me, audit_logs=audit_logs)

  def check(m) -> bool:
    return m.author.id == friday.user.id

  msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Kick"
  assert guild_user.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_user.me.id})" in msg.embeds[0].description
  assert guild_friday.owner and guild_friday.owner.mention in msg.embeds[0].description
  assert f"(ID: {guild_friday.owner.id})" in msg.embeds[0].description
  if reason:
    assert reason in msg.embeds[0].description
  else:
    assert "No reason given" in msg.embeds[0].description


@pytest.mark.skip("Not implemented")
async def test_unmutes_from_commands(friday: Friday):
  ...


@pytest.mark.skip("Not implemented")
@pytest.mark.parametrize("reason", ["", "big sus times", "lajks hdlkjahs lkjdhlaksjhdlkj ashlkdjhaslk"])
async def test_timeouts_from_automod(friday: Friday, logs: List[discord.AuditLogEntry], bot: UnitTester, guild_friday: Guild, guild: Guild, guild_user: Guild, channel: TextChannel, reason: str):
  ...

  async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
    for log in logs[1:limit]:
      if log.action == action and log.user == user:
        yield log
    oldest_log = logs[0]
    oldest_log.action = discord.AuditLogAction.member_role_update
    oldest_log.reason = reason
    oldest_log._target_id = guild_user.me.id
    oldest_log.user = guild_friday.me
    oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
    yield oldest_log

  # new_me = guild_user.me
  # new_me.roles.append(discord.Object(id=))

  friday.dispatch("member_update", before=guild_user.me, after=None, audit_logs=audit_logs)

  def check(m) -> bool:
    return m.author.id == friday.user.id

  msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Kick"
  assert guild_user.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_user.me.id})" in msg.embeds[0].description
  assert guild_friday.me and guild_friday.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_friday.me.id})" in msg.embeds[0].description
  if reason:
    assert reason in msg.embeds[0].description
  else:
    assert "No reason given" in msg.embeds[0].description


@pytest.mark.skip("Not implemented")
@pytest.mark.parametrize("reason", ["", "being stupid", "sus"])
async def test_timeouts_not_friday(friday: Friday, logs: List[discord.AuditLogEntry], bot: UnitTester, guild_friday: Guild, guild: Guild, guild_user: Guild, channel: TextChannel, reason: str):
  ...

  async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
    for log in logs[1:limit]:
      if log.action == action and log.user == user:
        yield log
    oldest_log = logs[0]
    oldest_log.action = discord.AuditLogAction.member_role_update
    oldest_log.reason = reason
    oldest_log._target_id = guild_user.me.id
    oldest_log.user = guild_friday.owner
    oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
    yield oldest_log

  friday.dispatch("member_update", member=guild_user.me, audit_logs=audit_logs)

  def check(m) -> bool:
    return m.author.id == friday.user.id

  msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Kick"
  assert guild_user.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_user.me.id})" in msg.embeds[0].description
  assert guild_friday.owner and guild_friday.owner.mention in msg.embeds[0].description
  assert f"(ID: {guild_friday.owner.id})" in msg.embeds[0].description
  if reason:
    assert reason in msg.embeds[0].description
  else:
    assert "No reason given" in msg.embeds[0].description


@pytest.mark.skip("Not implemented")
async def test_timeouts_from_commands(friday: Friday):
  ...


@pytest.mark.skip("Not implemented")
@pytest.mark.parametrize("reason", ["", "big sus times", "lajks hdlkjahs lkjdhlaksjhdlkj ashlkdjhaslk"])
async def test_untimeouts_from_automod(friday: Friday, logs: List[discord.AuditLogEntry], bot: UnitTester, guild_friday: Guild, guild: Guild, guild_user: Guild, channel: TextChannel, reason: str):
  ...

  async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
    for log in logs[1:limit]:
      if log.action == action and log.user == user:
        yield log
    oldest_log = logs[0]
    oldest_log.action = discord.AuditLogAction.member_role_update
    oldest_log.reason = reason
    oldest_log._target_id = guild_user.me.id
    oldest_log.user = guild_friday.me
    oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
    yield oldest_log

  # new_me = guild_user.me
  # new_me.roles.append(discord.Object(id=))

  friday.dispatch("member_update", before=guild_user.me, after=None, audit_logs=audit_logs)

  def check(m) -> bool:
    return m.author.id == friday.user.id

  msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Kick"
  assert guild_user.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_user.me.id})" in msg.embeds[0].description
  assert guild_friday.me and guild_friday.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_friday.me.id})" in msg.embeds[0].description
  if reason:
    assert reason in msg.embeds[0].description
  else:
    assert "No reason given" in msg.embeds[0].description


@pytest.mark.skip("Not implemented")
@pytest.mark.parametrize("reason", ["", "being stupid", "sus"])
async def test_untimeouts_not_friday(friday: Friday, logs: List[discord.AuditLogEntry], bot: UnitTester, guild_friday: Guild, guild: Guild, guild_user: Guild, channel: TextChannel, reason: str):
  ...

  async def audit_logs(limit: Optional[int] = 100, before=..., after=..., oldest_first: bool = False, user: discord.abc.Snowflake = ..., action=...) -> AsyncIterator[discord.audit_logs.AuditLogEntry]:
    for log in logs[1:limit]:
      if log.action == action and log.user == user:
        yield log
    oldest_log = logs[0]
    oldest_log.action = discord.AuditLogAction.member_role_update
    oldest_log.reason = reason
    oldest_log._target_id = guild_user.me.id
    oldest_log.user = guild_friday.owner
    oldest_log.created_at = discord.utils.utcnow() - datetime.timedelta(seconds=1)
    yield oldest_log

  friday.dispatch("member_update", member=guild_user.me, audit_logs=audit_logs)

  def check(m) -> bool:
    return m.author.id == friday.user.id

  msg = await bot.wait_for("message", check=check, timeout=pytest.timeout)  # type: ignore
  assert msg.embeds[0].title == "Kick"
  assert guild_user.me.mention in msg.embeds[0].description
  assert f"(ID: {guild_user.me.id})" in msg.embeds[0].description
  assert guild_friday.owner and guild_friday.owner.mention in msg.embeds[0].description
  assert f"(ID: {guild_friday.owner.id})" in msg.embeds[0].description
  if reason:
    assert reason in msg.embeds[0].description
  else:
    assert "No reason given" in msg.embeds[0].description


@pytest.mark.skip("Not implemented")
async def test_untimeouts_from_commands(friday: Friday):
  ...
