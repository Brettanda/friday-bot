import asyncio
import logging
import os

import discord
from discord.ext import tasks
from dotenv import load_dotenv

from functions.mysql_connection import query_prefix
from index import Friday

load_dotenv()
TOKEN = os.environ.get('TOKENTEST')

intents = discord.Intents.default()

class Friday_testing(Friday):
  def __init__(self,*args,**kwargs):
    super().__init__(*args,**kwargs)

    self.test_stop.start()

  @tasks.loop(minutes=1)
  async def test_stop(self):
    await self.wait_until_ready()
    await asyncio.sleep(3)
    assert await self.close()

def test_will_it_blend():
  bot = Friday_testing(command_prefix=query_prefix or "!",case_insensitive=True,intents=intents,owner_id=215227961048170496)
  loop = asyncio.get_event_loop()
  try:
    loop.run_until_complete(bot.start(TOKEN,bot=True))
  except KeyboardInterrupt:
    # mydb.close()
    logging.info("STOPED")
    loop.run_until_complete(bot.close())
  finally:
    loop.close()
