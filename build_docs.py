import asyncio
import logging
import os

from dotenv import load_dotenv

from functions import build_docs
from index import Friday

# from create_trans_key import run

load_dotenv(dotenv_path="./.env")
TOKEN = os.environ.get('TOKENTEST')


class Friday_testing(Friday):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  async def on_ready(self):
    build_docs(self, "!")
    await asyncio.sleep(2)
    await self.close()

# TODO: Add a check for functions modules/files not being named the same as the functions/defs


# def test_translate_key_gen():
#   run()
if __name__ == "__main__":
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
