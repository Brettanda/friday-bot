import asyncio
import logging
# import os
import sys

import discord
from discord.ext import tasks
from dotenv import load_dotenv

import functions
from index import Friday
from launcher import setup_logging

# from create_trans_key import run

load_dotenv(dotenv_path="./.env")
# TOKEN = os.environ.get('TOKENTEST')


class Friday_testing(Friday):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    # self.test_stop.start()
    # self.test_message.start()

  # async def setup(self, load_extentions=False):
  #   for cog in cogs.default:
  #     await self.load_extension(f"cogs.{cog}")
  #   return await super().setup(load_extentions=load_extentions)

  async def channel(self) -> discord.TextChannel:
    return self.get_channel(892840236781015120) if self.get_channel(892840236781015120) is None else await self.fetch_channel(892840236781015120)  # type: ignore

  async def on_ready(self):
    await (await self.channel()).send("?ready")

    try:
      def online_check(m) -> bool:
        return m.author.id == 892865928520413245 and m.channel.id == 892840236781015120
      await self.wait_for("message", check=online_check, timeout=3.0)
    except asyncio.TimeoutError:
      return await self.close()

    def pass_check(m) -> bool:
      return m.author.id == 892865928520413245 and (m.content in ("!passed", "!failed", "!complete"))

    await self.wait_for("message", check=pass_check, timeout=120.0)
    await self.close()

  @tasks.loop()
  async def test_message(self):
    print("passed")

  @tasks.loop(seconds=1, count=1)
  async def test_stop(self):
    await self.wait_until_ready()
    while not self.ready:
      await asyncio.sleep(0.1)
    assert await super().close()


# TODO: Add a check for functions modules/files not being named the same as the functions/defs

# def test_translate_key_gen():
#   run()

formatter = logging.Formatter("%(levelname)s:%(name)s: %(message)s")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)

logger = logging.getLogger("Friday")
logger.handlers = [handler]
logger.setLevel(logging.INFO)


def test_will_it_blend():
  bot = Friday_testing()

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

  asyncio.run(main(bot))

# import asyncio
# import os
# import pytest
# import discord
# # from discord.ext import tasks, commands
# from dotenv import load_dotenv

# from index import Friday
# import cogs

# # from create_trans_key import run

# load_dotenv(dotenv_path="./.env")
# TOKEN = os.environ.get('TOKENTEST')


# class Friday_testing(Friday):
#   def __init__(self, loop=None, *args, **kwargs):
#     self.loop = loop
#     super().__init__(loop=self.loop, *args, **kwargs)

#     # self.test_stop.start()
#     # self.test_message.start()

#   async def setup(self, load_extentions=False):
#     for cog in cogs.default:
#       self.load_extension(f"cogs.{cog}")
#     return await super().setup(load_extentions=load_extentions)

#   # @tasks.loop()
#   # async def test_message(self):
#   #   print("passed")

#   # @tasks.loop(seconds=1, count=1)
#   # async def test_stop(self):
#   #   await self.wait_until_ready()
#   #   while not self.ready:
#   #     await asyncio.sleep(0.1)
#   #   assert await super().close()


# # TODO: Add a check for functions modules/files not being named the same as the functions/defs

# # def test_translate_key_gen():
# #   run()

# @pytest.fixture(scope="session")
# def event_loop():
#   return asyncio.get_event_loop()


# @pytest.fixture(scope="session", autouse=True)
# async def bot(event_loop) -> Friday_testing:
#   bot = Friday_testing(loop=event_loop)
#   event_loop.create_task(bot.start(TOKEN))
#   await bot.wait_until_ready()
#   return bot


# @pytest.fixture(scope="session", autouse=True)
# def cleanup(request, bot):
#   def close():
#     asyncio.get_event_loop().run_until_complete(bot.close())
#   request.addfinalizer(close)


# @pytest.mark.asyncio
# async def test_will_it_blend(bot):
#   assert bot.status == discord.Status.online
#   # bot = Friday_testing()
#   # loop = asyncio.get_event_loop()
#   # try:
#   #   loop.run_until_complete(bot.start(TOKEN))
#   # except KeyboardInterrupt:
#   #   # mydb.close()
#   #   logging.info("STOPED")
#   #   loop.run_until_complete(bot.close())
#   # finally:
#   #   loop.close()
