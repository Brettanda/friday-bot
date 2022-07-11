from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import asyncpg
from discord.ext import commands

from functions import cache

if TYPE_CHECKING:
  from functions.custom_contexts import MyContext
  from index import Friday

log = logging.getLogger(__name__)


class Config:
  __slots__ = ("bot", "id", "shortcuts", )

  def __init__(self, *, record: asyncpg.Record, bot: Friday):
    self.bot: Friday = bot
    self.id: int = int(record["id"], base=10)
    self.shortcuts: dict = record["shortcuts"]


class Shortcuts(commands.Cog):
  def __init__(self, bot: Friday):
    self.bot: Friday = bot

    # shortcuts = bot.command_group("shortcuts", "Shortcut commands")

    # @shortcuts.command()
    # async def add(self, ctx: MyContext, shortcut: str, *, command: str):
    #   ...

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  def cog_check(self, ctx: MyContext):
    if not ctx.guild:
      raise commands.NoPrivateMessage()
    return True

  @cache.cache()
  async def get_guild_config(self, guild_id: int, *, connection: Optional[asyncpg.Connection] = None) -> Optional[Config]:
    conn = connection or self.bot.pool
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1;"
    record = await conn.fetchrow(query, str(guild_id))
    log.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
    if record is not None:
      return Config(record=record, bot=self.bot)
    return None

  @commands.group(name="shortcuts", aliases=["sc"], help="Setup shortcuts for your favourite commands and arguments")
  async def shortcuts(self, ctx: MyContext):
    ...

  @shortcuts.command(name="add", aliases=["a", "+"], help="Add a shortcut")
  async def shortcuts_add(self, ctx: MyContext, shortcut: str, command: commands.Command, *, args: Optional[str] = None):
    ...

  @shortcuts.command(name="remove", aliases=["r", "-"], help="Remove a shortcut")
  async def shortcuts_remove(self, ctx: MyContext, shortcut: str):
    ...

  @shortcuts.command(name="list", aliases=["l", "ls"], help="List all shortcuts")
  async def shortcuts_list(self, ctx: MyContext):
    ...

  @shortcuts.command(name="clear", aliases=["c", "clr"], help="Clear all shortcuts")
  async def shortcuts_clear(self, ctx: MyContext):
    ...


async def setup(bot):
  ...
  # await bot.add_cog(Shortcuts(bot))
