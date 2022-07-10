from __future__ import annotations

import asyncio

# import discord
import pytest

# import os
# import sys
# import time
# from typing import Callable, Optional

# from discord.ext import commands
# from dotenv import load_dotenv

# import index
# from launcher import setup_logging


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
  return asyncio.new_event_loop()


# @pytest.fixture(scope="session", autouse=True)
# async def cleanup(request, event_loop: asyncio.AbstractEventLoop):
#   def close():
#     # try:
#     #   event_loop.close()
#     #   event_loop_friday.close()
#     #   event_loop_user.close()
#     # except (RuntimeError, StopAsyncIteration):
#     #   pass
#     try:
#       asyncio.get_event_loop().run_until_complete(bot.close())
#     except (RuntimeError, StopAsyncIteration):
#       pass
#     try:
#       asyncio.get_event_loop().run_until_complete(friday.close())
#     except (RuntimeError, StopAsyncIteration):
#       pass
#     try:
#       asyncio.get_event_loop().run_until_complete(bot_user.close())
#     except (RuntimeError, StopAsyncIteration):
#       pass
#   request.addfinalizer(close)
