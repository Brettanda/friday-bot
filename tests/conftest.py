from __future__ import annotations

import asyncio
import os
# import sys
import time

import discord
import pytest
from discord.ext import commands
from dotenv import load_dotenv

import index
from launcher import get_logger

load_dotenv()

TOKEN = os.environ.get('TOKENUNITTEST')
FRIDAYTOKEN = os.environ.get('TOKENTEST')
TOKENUSER = os.environ.get('TOKENUNITTESTUSER')


class UnitTester(commands.Bot):
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
    guild = self.get_guild(243159711237537802)
    await guild.chunk(cache=True)
    main = guild.get_member(751680714948214855)
    if main.status not in (discord.Status.online, discord.Status.idle):
      def check_online(m):
        return m.author.id == 751680714948214855 and m.channel.id == 892840236781015120
      await self.wait_for("message", check=check_online, timeout=30.0)
    else:
      self.was_online = True


class Friday(index.Friday):
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.x = 0


class UnitTesterUser(UnitTester):
  pass


@pytest.fixture(scope="session")
def event_loop():
  loop = asyncio.new_event_loop()
  yield loop
  loop.close()


@pytest.fixture(scope="session")
def event_loop_friday():
  loop = asyncio.new_event_loop()
  yield loop
  loop.close()


@pytest.fixture(scope="session")
def event_loop_user():
  loop = asyncio.new_event_loop()
  yield loop
  loop.close()


@pytest.fixture(scope="session")
async def bot(event_loop: event_loop) -> commands.Bot:
  bot = UnitTester()
  event_loop.create_task(bot.start(TOKEN))
  yield bot
  await bot.close()


@pytest.fixture(scope="session")
async def friday(event_loop_friday: event_loop_friday) -> Friday:
  async def main(bot):
    async with bot:
      await bot.start(FRIDAYTOKEN, reconnect=True)
  log = get_logger("Friday")
  bot = Friday(logger=log)
  asyncio.create_task(main(bot))
  yield bot
  await bot.close()


@pytest.fixture(scope="session")
async def bot_user(event_loop: event_loop_user) -> commands.Bot:
  bot_user = UnitTesterUser()
  event_loop.create_task(bot_user.start(TOKENUSER))
  yield bot_user
  await bot_user.close()


# @pytest.fixture(scope="session", autouse=True)
# async def cleanup(request, bot, bot_user, channel):
#   def close():
#     ...
#     # if bot and not bot.was_online:
#     # asyncio.get_event_loop().run_until_complete(channel.send("!complete"))
#     # if bot_user and not bot_user.was_online:
#     #   asyncio.get_event_loop().run_until_complete(channel.send("!complete"))
#   request.addfinalizer(close)


@pytest.fixture(autouse=True)
async def slow_down_tests(bot):
  await bot.wait_until_ready()
  yield
  bot.x += 1
  if bot.x % 3 == 0:
    time.sleep(1)


@pytest.fixture(autouse=True)
async def slow_down_friday(friday: friday):
  await friday.wait_until_ready()
  yield
  friday.x += 1
  if friday.x % 3 == 0:
    time.sleep(1)


@pytest.fixture(autouse=True)
async def slow_down_tests_user(bot_user):
  await bot_user.wait_until_ready()
  yield
  bot_user.x += 1
  if bot_user.x % 3 == 0:
    time.sleep(1)


@pytest.fixture(scope="session")
async def guild(bot: UnitTester) -> discord.Guild:
  await bot.wait_until_ready()
  yield bot.get_guild(243159711237537802)


@pytest.fixture(scope="session")
async def channel(bot, guild: guild) -> discord.TextChannel:
  await bot.wait_until_ready()
  yield guild.get_channel(892840236781015120) or await guild.fetch_channel(892840236781015120)


@pytest.fixture(scope="session")
async def voice_channel(bot, guild: guild) -> discord.VoiceChannel:
  await bot.wait_until_ready()
  yield guild.get_channel(895486009465266176) or await guild.fetch_channel(895486009465266176)


@pytest.fixture(scope="session")
async def user(bot, guild: guild) -> discord.User:
  await bot.wait_until_ready()
  yield await guild.fetch_user(813618591878086707)


@pytest.fixture(scope="session")
async def guild_user(bot_user) -> discord.Guild:
  await bot_user.wait_until_ready()
  yield bot_user.get_guild(243159711237537802)


@pytest.fixture(scope="session")
async def channel_user(bot_user, guild_user: guild_user) -> discord.TextChannel:
  await bot_user.wait_until_ready()
  yield guild_user.get_channel(892840236781015120) or await guild_user.fetch_channel(892840236781015120)


@pytest.fixture(scope="session")
async def voice_channel_user(bot_user, guild_user: guild) -> discord.VoiceChannel:
  await bot_user.wait_until_ready()
  yield guild_user.get_channel(895486009465266176) or await guild_user.fetch_channel(895486009465266176)


@pytest.fixture(scope="session")
async def user_user(bot_user, guild_user: guild) -> discord.User:
  await bot_user.wait_until_ready()
  yield await guild_user.fetch_user(813618591878086707)


def msg_check(msg: discord.Message, content: str = None) -> bool:
  is_reference = (msg.reference is not None and msg.reference.cached_message is not None and (msg.reference.cached_message.author.id == 892865928520413245 or msg.reference.cached_message.author.id == 968261189828231308))
  if content is not None and is_reference:
    return msg.channel.id == 892840236781015120 and msg.author.id == 751680714948214855 and is_reference and content.strip() == msg.reference.cached_message.content
  return msg.channel.id == 892840236781015120 and msg.author.id == 751680714948214855 and is_reference


def raw_message_delete_check(payload: discord.RawMessageDeleteEvent, msg: discord.Message) -> bool:
  return payload.message_id == msg.id


def pytest_configure():
  pytest.timeout = 8.0
  pytest.msg_check = msg_check
  pytest.raw_message_delete_check = raw_message_delete_check
