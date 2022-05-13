from __future__ import annotations

import asyncio
import os
# import sys
import time
from typing import Callable

import discord
import pytest
from discord.ext import commands
from dotenv import load_dotenv

import index
from launcher import get_logger

load_dotenv()

TOKEN = os.environ['TOKENUNITTEST']
FRIDAYTOKEN = os.environ['TOKENTEST']
TOKENUSER = os.environ['TOKENUNITTESTUSER']


class UnitTester(commands.Bot):
  user: discord.ClientUser

  def __init__(self, **kwargs):
    self.was_online = False
    super().__init__(
        command_prefix="?",
        intents=discord.Intents.all(),
        status=discord.Status.do_not_disturb,
        allowed_mentions=discord.AllowedMentions.all(),
        **kwargs
    )
    self.x = 0

  async def on_message(self, msg: discord.Message):
    if msg.author.id != 751680714948214855:
      return

    await self.process_commands(msg)

  async def on_ready(self):
    print("Ready")
    await self.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name="Unit Testing"
        ))


class Friday(index.Friday):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.x = 0


class UnitTesterUser(UnitTester):
  pass


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
  return asyncio.new_event_loop()


@pytest.fixture(scope="session")
def event_loop_friday() -> asyncio.AbstractEventLoop:
  return asyncio.new_event_loop()


@pytest.fixture(scope="session")
def event_loop_user() -> asyncio.AbstractEventLoop:
  return asyncio.new_event_loop()


@pytest.fixture(scope="session")
async def bot(event_loop: asyncio.AbstractEventLoop) -> UnitTester:
  bot = UnitTester()
  event_loop.create_task(bot.start(TOKEN))
  return bot


@pytest.fixture(scope="session")
async def friday(event_loop_friday: asyncio.AbstractEventLoop) -> Friday:
  async def main(bot):
    async with bot:
      await bot.start(FRIDAYTOKEN, reconnect=True)
  log = get_logger("Friday")
  bot = Friday(logger=log)
  asyncio.create_task(main(bot))
  return bot


@pytest.fixture(scope="session")
async def bot_user(event_loop: asyncio.AbstractEventLoop) -> UnitTesterUser:
  bot_user = UnitTesterUser()
  event_loop.create_task(bot_user.start(TOKENUSER))
  return bot_user


@pytest.fixture(scope="session", autouse=True)
async def cleanup(request, bot: UnitTester, friday: Friday, bot_user: UnitTesterUser, event_loop: asyncio.AbstractEventLoop, event_loop_friday: asyncio.AbstractEventLoop, event_loop_user: asyncio.AbstractEventLoop):  # bot, bot_user, channel):
  def close():
    asyncio.get_event_loop().run_until_complete(bot.close())
    asyncio.get_event_loop().run_until_complete(friday.close())
    asyncio.get_event_loop().run_until_complete(bot_user.close())
    event_loop.close()
    event_loop_friday.close()
    event_loop_user.close()
  request.addfinalizer(close)


@pytest.fixture(autouse=True)
async def slow_down_tests(bot: UnitTester):
  await bot.wait_until_ready()
  yield
  bot.x += 1
  if bot.x % 3 == 0:
    time.sleep(1)


@pytest.fixture(autouse=True)
async def slow_down_friday(friday: Friday):
  await friday.wait_until_ready()
  yield
  friday.x += 1
  if friday.x % 3 == 0:
    time.sleep(1)


@pytest.fixture(autouse=True)
async def slow_down_tests_user(bot_user: UnitTesterUser):
  await bot_user.wait_until_ready()
  yield
  bot_user.x += 1
  if bot_user.x % 3 == 0:
    time.sleep(1)


@pytest.fixture(scope="session")
async def guild(bot: UnitTester) -> discord.Guild:
  await bot.wait_until_ready()
  guild = bot.get_guild(243159711237537802)
  if not guild:
    raise RuntimeError("Guild not found")
  return guild


@pytest.fixture(scope="session")
async def channel(bot: UnitTester, guild) -> discord.TextChannel:
  await bot.wait_until_ready()
  return guild.get_channel(892840236781015120) or await guild.fetch_channel(892840236781015120)


@pytest.fixture(scope="session")
async def voice_channel(bot: UnitTester, guild) -> discord.VoiceChannel:
  await bot.wait_until_ready()
  return guild.get_channel(895486009465266176) or await guild.fetch_channel(895486009465266176)


@pytest.fixture(scope="session")
async def user(bot: UnitTester, guild) -> discord.User:
  await bot.wait_until_ready()
  return await guild.fetch_user(813618591878086707)


@pytest.fixture(scope="session")
async def guild_user(bot_user: UnitTesterUser) -> discord.Guild:
  await bot_user.wait_until_ready()
  guild = bot_user.get_guild(243159711237537802)
  if not guild:
    raise RuntimeError("Guild not found")
  return guild


@pytest.fixture(scope="session")
async def channel_user(bot_user: UnitTesterUser, guild_user) -> discord.TextChannel:
  await bot_user.wait_until_ready()
  return guild_user.get_channel(892840236781015120) or await guild_user.fetch_channel(892840236781015120)


@pytest.fixture(scope="session")
async def voice_channel_user(bot_user: UnitTesterUser, guild_user) -> discord.VoiceChannel:
  await bot_user.wait_until_ready()
  return guild_user.get_channel(895486009465266176) or await guild_user.fetch_channel(895486009465266176)


@pytest.fixture(scope="session")
async def user_user(bot_user: UnitTesterUser, guild_user) -> discord.User:
  await bot_user.wait_until_ready()
  return await guild_user.fetch_user(813618591878086707)


@pytest.fixture(scope="session")
async def guild_friday(friday: Friday) -> discord.Guild:
  await friday.wait_until_ready()
  guild = friday.get_guild(243159711237537802)
  if not guild:
    raise RuntimeError("Guild not found")
  return guild


@pytest.fixture(scope="session")
async def channel_friday(friday: Friday, guild_user) -> discord.TextChannel:
  await friday.wait_until_ready()
  return guild_user.get_channel(892840236781015120) or await guild_user.fetch_channel(892840236781015120)


@pytest.fixture(scope="session")
async def voice_channel_friday(friday: Friday, guild_user) -> discord.VoiceChannel:
  await friday.wait_until_ready()
  return guild_user.get_channel(895486009465266176) or await guild_user.fetch_channel(895486009465266176)


@pytest.fixture(scope="session")
async def user_friday(friday: Friday, guild_user) -> discord.User:
  await friday.wait_until_ready()
  return await guild_user.fetch_user(813618591878086707)


def msg_check(new_msg: discord.Message, command_message: discord.Message) -> bool:
  assert new_msg.author != command_message.author
  assert new_msg.reference is not None
  return new_msg.reference.message_id == command_message.id


def raw_message_delete_check(payload: discord.RawMessageDeleteEvent, msg: discord.Message) -> bool:
  return payload.message_id == msg.id


def pytest_configure() -> None:
  # setattr(pytest, "timeout", 8.0)
  # setattr(pytest, "msg_check", msg_check)
  # setattr(pytest, "raw_message_delete_check", raw_message_delete_check)

  pytest.timeout: float = 8.0  # type: ignore
  pytest.msg_check: Callable = msg_check  # type: ignore
  pytest.raw_message_delete_check: Callable = raw_message_delete_check  # type: ignore
