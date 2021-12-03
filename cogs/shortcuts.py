# import discord
from discord.ext import commands

from functions import MyContext, cache
from typing import Optional
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class Config:
  __slots__ = ("bot", "id", "shortcuts", )

  @classmethod
  async def from_record(cls, record, bot):
    self = cls()

    self.bot = bot
    self.id: int = int(record["id"], base=10)
    self.shortcuts: dict = record["shortcuts"]
    return self


class Shortcuts(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot

    # shortcuts = bot.command_group("shortcuts", "Shortcut commands")

    # @shortcuts.command()
    # async def add(self, ctx: MyContext, shortcut: str, *, command: str):
    #   ...

  def __repr__(self) -> str:
    return "<cogs.Shortcuts>"

  def cog_check(self, ctx: MyContext):
    if not ctx.guild:
      raise commands.NoPrivateMessage()
    return True

  @cache.cache()
  async def get_guild_config(self, guild_id: int) -> Optional[Config]:
    query = "SELECT * FROM servers WHERE id=$1 LIMIT 1;"
    async with self.bot.db.pool.acquire(timeout=300.0) as conn:
      record = await conn.fetchrow(query, str(guild_id))
      self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
      if record is not None:
        return await Config.from_record(record, self.bot)
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


def setup(bot):
  ...
  # bot.add_cog(Shortcuts(bot))
