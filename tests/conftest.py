import asyncio
import os
import pytest
import sys
# import time

import nextcord as discord
from nextcord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get('TOKENUNITTEST')


class UnitTester(commands.Bot):
  def __init__(self, loop=None, **kwargs):
    self.loop = loop
    self.was_online = False
    super().__init__(
        command_prefix="?",
        intents=discord.Intents.all(),
        status=discord.Status.do_not_disturb,
        allowed_mentions=discord.AllowedMentions.all(),
        loop=self.loop, **kwargs
    )

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


@pytest.fixture(scope="session")
def event_loop():
  return asyncio.get_event_loop()


@pytest.fixture(scope="session")
async def bot(event_loop) -> commands.Bot:
  bot = UnitTester(loop=event_loop)
  event_loop.create_task(bot.start(TOKEN))
  await bot.wait_until_ready()
  guild = bot.get_guild(243159711237537802)
  await guild.chunk(cache=True)
  main = guild.get_member(751680714948214855)
  if main.status not in (discord.Status.online, discord.Status.idle):
    def check_online(m):
      return m.author.id == 751680714948214855 and m.channel.id == 892840236781015120
    await bot.wait_for("message", check=check_online, timeout=30.0)
  else:
    bot.was_online = True
  return bot


@pytest.fixture(scope="session", autouse=True)
def cleanup(request, bot, channel):
  def close():
    if not bot.was_online:
      asyncio.get_event_loop().run_until_complete(channel.send("!complete"))
    if sys.gettrace() is None:
      asyncio.get_event_loop().run_until_complete(channel.purge(limit=None, oldest_first=True))
    asyncio.get_event_loop().run_until_complete(bot.close())
  request.addfinalizer(close)


# @pytest.fixture(autouse=True)
# def slow_down_tests():
#   yield
#   time.sleep(0.5)


@pytest.fixture(scope="session")
async def channel(bot: commands.Bot) -> discord.TextChannel:
  return await bot.fetch_channel(892840236781015120)


@pytest.fixture(scope="session")
async def voice_channel(bot: commands.Bot) -> discord.VoiceChannel:
  return await bot.fetch_channel(895486009465266176)


@pytest.fixture(scope="session")
async def user(bot: commands.Bot) -> discord.User:
  return await bot.fetch_user(813618591878086707)


def msg_check(msg: discord.Message, content: str = None) -> bool:
  is_reference = (msg.reference is not None and msg.reference.cached_message is not None and msg.reference.cached_message.author.id == 892865928520413245)
  if content is not None and is_reference:
    return msg.channel.id == 892840236781015120 and msg.author.id == 751680714948214855 and is_reference and content.strip() == msg.reference.cached_message.content
  return msg.channel.id == 892840236781015120 and msg.author.id == 751680714948214855 and is_reference


def raw_message_delete_check(payload: discord.RawMessageDeleteEvent, msg: discord.Message) -> bool:
  return payload.message_id == msg.id


def pytest_configure():
  pytest.timeout = 8.0
  pytest.msg_check = msg_check
  pytest.raw_message_delete_check = raw_message_delete_check
