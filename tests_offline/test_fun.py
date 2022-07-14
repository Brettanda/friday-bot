from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from async_timeout import timeout
from discord.ext.commands import BadArgument

from cogs.fun import Fun

if TYPE_CHECKING:
  ...

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("size", range(0, 10))
@pytest.mark.parametrize("bombs", range(0, 20))
async def test_minesweeper(event_loop, size: int, bombs: int):
  class bot:
    loop = event_loop
  fun = Fun(bot)  # type: ignore
  async with timeout(0.1, loop=event_loop):
    try:
      mines = await event_loop.run_in_executor(None, fun.mine_sweeper, size, bombs)
    except BadArgument:
      assert True
    else:
      print(f"completed {size} {bombs}")
      assert mines.count("💥") <= bombs
