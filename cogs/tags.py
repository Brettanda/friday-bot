import discord
from discord.ext import commands

from functions import cache

from typing import Optional
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


async def tags_autocomplete(ctx):
  config = await ctx.cog.get_guild_config(ctx.interaction.guild_id)
  if config is None or config.tags is None or len(config.tags) == 0:
    return []
  return [str(i) for i in config.tags.keys()]


class Config:
  __slots__ = ("bot", "id", "tags", )

  @classmethod
  async def from_record(cls, record, bot):
    self = cls()

    self.bot = bot
    self.id: int = int(record["id"], base=10)
    self.tags: dict = record["tags"]
    return self


class Tags(commands.Cog):
  """Ping? Pong!"""

  def __init__(self, bot: "Bot"):
    self.bot = bot

    # tags = bot.command_group("tags", "Tag editing commands")

    # @tags.command()
    # @discord.option("name", description="Tag name")
    # @discord.option("content", description="Tag content")
    # async def add(ctx, name: str, content: str):
    #   """Add a tag."""
    #   ...

  def __repr__(self) -> str:
    return "<cogs.Tags>"

  @cache.cache()
  async def get_guild_config(self, guild_id: int) -> Optional[Config]:
    query = "SELECT id,tags FROM servers WHERE id=$1 LIMIT 1;"
    async with self.bot.db.pool.acquire(timeout=300.0) as conn:
      record = await conn.fetchrow(query, str(guild_id))
      self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
      if record is not None:
        return await Config.from_record(record, self.bot)
      return None

  @commands.group(name="tag")
  async def norm_tags(self, ctx, tag: str):
    ...

  @norm_tags.command(name="create")
  async def norm_tags_create(self, ctx, tag: str, *, content: str):
    ...

  @norm_tags.command(name="delete")
  async def norm_tags_delete(self, ctx, tag: str):
    ...

  @norm_tags.command(name="list")
  async def norm_tags_list(self, ctx):
    ...

  @discord.slash_command(name="tag")
  @discord.option("tag", autocomplete=tags_autocomplete)
  async def slash_tag(self, ctx, tag: str):
    ...


def setup(bot):
  ...
  # bot.add_cog(Tags(bot))
