import asyncio
import logging
import os

from discord.ext import tasks
from dotenv import load_dotenv

from index import Friday

# from create_trans_key import run

load_dotenv(dotenv_path="./.env")
TOKEN = os.environ.get('TOKENTEST')


class Friday_testing(Friday):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.test_stop.start()

  @tasks.loop(minutes=1)
  async def test_stop(self):
    await self.wait_until_ready()
    await asyncio.sleep(3)
    assert await self.close()


# TODO: Add a check for functions modules/files not being named the same as the functions/defs

# def test_translate_key_gen():
#   run()


def test_will_it_blend():
  bot = Friday_testing()
  loop = asyncio.get_event_loop()
  try:
    loop.run_until_complete(bot.start(TOKEN, bot=True))
  except KeyboardInterrupt:
    # mydb.close()
    logging.info("STOPED")
    loop.run_until_complete(bot.close())
  finally:
    loop.close()
