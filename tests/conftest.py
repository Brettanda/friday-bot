from __future__ import annotations

import asyncio
import os
# import sys
import time
from typing import Callable, Optional
import functions
import discord
import pytest
from discord.ext import commands
from dotenv import load_dotenv

import index
from launcher import setup_logging

load_dotenv()

TOKEN = os.environ['TOKENUNITTEST']
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

    # if msg.author.id == self.user.id:
    #   self.x += 1

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
    self.testing = True
    self.the_message: Optional[discord.Message] = None

  async def on_message(self, m: discord.Message) -> None:
    if m.author.id == self.user.id:
      self.x += 1

    await self.process_commands(m)


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
    try:
      pool = await functions.db.create_pool()
    except Exception:
      print('Could not set up PostgreSQL. Exiting.')
      return

    with setup_logging():
      async with bot:
        bot.pool = pool
        await bot.start()

  bot = Friday()
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
    # try:
    #   event_loop.close()
    #   event_loop_friday.close()
    #   event_loop_user.close()
    # except (RuntimeError, StopAsyncIteration):
    #   pass
    try:
      asyncio.get_event_loop().run_until_complete(bot.close())
    except (RuntimeError, StopAsyncIteration):
      pass
    try:
      asyncio.get_event_loop().run_until_complete(friday.close())
    except (RuntimeError, StopAsyncIteration):
      pass
    try:
      asyncio.get_event_loop().run_until_complete(bot_user.close())
    except (RuntimeError, StopAsyncIteration):
      pass
  request.addfinalizer(close)


@pytest.fixture(autouse=True)
async def slow_down_tests(bot: UnitTester):
  return await bot.wait_until_ready()


@pytest.fixture(autouse=True)
async def slow_down_friday(friday: Friday):
  await friday.wait_until_ready()
  yield
  if friday.x % 3 == 0:
    friday.x = 0
    time.sleep(2)


@pytest.fixture(autouse=True)
async def slow_down_tests_user(bot_user: UnitTesterUser):
  return await bot_user.wait_until_ready()


async def get_guild(bot: Friday | UnitTester | UnitTesterUser) -> discord.Guild:
  await bot.wait_until_ready()
  guild = bot.get_guild(243159711237537802)
  if not guild:
    raise RuntimeError("Guild not found")
  return guild


async def get_channel(bot: Friday | UnitTester | UnitTesterUser, guild: discord.Guild) -> discord.TextChannel:
  await bot.wait_until_ready()
  return guild.get_channel(892840236781015120) or await guild.fetch_channel(892840236781015120)  # type: ignore


async def get_voice_channel(bot: Friday | UnitTester | UnitTesterUser, guild: discord.Guild) -> discord.VoiceChannel:
  await bot.wait_until_ready()
  return guild.get_channel(895486009465266176) or await guild.fetch_channel(895486009465266176)  # type: ignore


async def get_user(bot: Friday | UnitTester | UnitTesterUser, guild: discord.Guild) -> discord.Member:
  await bot.wait_until_ready()
  return await guild.fetch_member(813618591878086707)


@pytest.fixture(scope="session")
async def guild(bot: UnitTester) -> discord.Guild:
  return await get_guild(bot)


@pytest.fixture(scope="session")
async def channel(bot: UnitTester, guild: discord.Guild) -> discord.TextChannel:
  return await get_channel(bot, guild)


@pytest.fixture(scope="session")
async def voice_channel(bot: UnitTester, guild: discord.Guild) -> discord.VoiceChannel:
  return await get_voice_channel(bot, guild)


@pytest.fixture(scope="session")
async def user(bot: UnitTester, guild: discord.Guild) -> discord.Member:
  return await get_user(bot, guild)


@pytest.fixture(scope="session")
async def guild_user(bot_user: UnitTesterUser) -> discord.Guild:
  return await get_guild(bot_user)


@pytest.fixture(scope="session")
async def channel_user(bot_user: UnitTesterUser, guild_user: discord.Guild) -> discord.TextChannel:
  return await get_channel(bot_user, guild_user)


@pytest.fixture(scope="session")
async def voice_channel_user(bot_user: UnitTesterUser, guild_user: discord.Guild) -> discord.VoiceChannel:
  return await get_voice_channel(bot_user, guild_user)


@pytest.fixture(scope="session")
async def user_user(bot_user: UnitTesterUser, guild_user: discord.Guild) -> discord.Member:
  return await get_user(bot_user, guild_user)


@pytest.fixture(scope="session")
async def guild_friday(friday: Friday) -> discord.Guild:
  return await get_guild(friday)


@pytest.fixture(scope="session")
async def channel_friday(friday: Friday, guild_friday: discord.Guild) -> discord.TextChannel:
  return await get_channel(friday, guild_friday)


@pytest.fixture(scope="session")
async def voice_channel_friday(friday: Friday, guild_friday: discord.Guild) -> discord.VoiceChannel:
  return await get_voice_channel(friday, guild_friday)


@pytest.fixture(scope="session")
async def user_friday(friday: Friday, guild_friday: discord.Guild) -> discord.Member:
  return await get_user(friday, guild_friday)


async def send_command(bot: Friday | UnitTester | UnitTesterUser, channel: discord.TextChannel, command: str) -> discord.Message:
  com = await channel.send(command)
  assert com
  return com


def msg_check(new_msg: discord.Message, command_message: discord.Message) -> bool:
  return new_msg.author.id != command_message.author.id and \
      new_msg.reference is not None and \
      new_msg.reference.message_id == command_message.id


def raw_message_delete_check(payload: discord.RawMessageDeleteEvent, msg: discord.Message) -> bool:
  return payload.message_id == msg.id


def pytest_configure() -> None:
  # setattr(pytest, "timeout", 8.0)
  # setattr(pytest, "msg_check", msg_check)
  # setattr(pytest, "raw_message_delete_check", raw_message_delete_check)

  pytest.timeout: float = 8.0  # type: ignore
  # pytest.send_command: Callable = send_command  # type: ignore
  # pytest.msg_check: Callable = msg_check  # type: ignore
  pytest.raw_message_delete_check: Callable = raw_message_delete_check  # type: ignore
