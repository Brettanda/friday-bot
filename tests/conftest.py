import asyncio
import os
import sys
import pytest

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get('TOKENUNITTEST')


class UnitTester(commands.Bot):
  def __init__(self, loop=None, **kwargs):
    self.loop = loop
    super().__init__(
        command_prefix="?",
        intents=discord.Intents(messages=True, reactions=True),
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


@pytest.fixture(scope="session", autouse=True)
async def bot(event_loop) -> commands.Bot:
  bot = UnitTester(loop=event_loop)
  event_loop.create_task(bot.start(TOKEN))
  await bot.wait_until_ready()
  return bot


@pytest.fixture(scope="session", autouse=True)
def cleanup(request, bot, channel):
  def close():
    asyncio.get_event_loop().run_until_complete(channel.purge(oldest_first=True))
    asyncio.get_event_loop().run_until_complete(bot.close())
  request.addfinalizer(close)


@pytest.fixture(scope="session", autouse=True)
async def channel(bot: commands.Bot) -> discord.TextChannel:
  return await bot.fetch_channel(892840236781015120)


def msg_check(msg: discord.Message) -> bool:
  return msg.channel.id == 892840236781015120 and msg.author.id == 751680714948214855 and (msg.reference is not None and msg.reference.cached_message is not None and msg.reference.cached_message.author.id == 892865928520413245)


def pytest_configure():
  pytest.timeout = 8.0
  pytest.msg_check = msg_check
