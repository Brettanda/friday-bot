import asyncpg
import os
import json

import discord
from discord.ext import commands, tasks
from typing_extensions import TYPE_CHECKING
from typing import Union

if TYPE_CHECKING:
  from index import Friday as Bot


class Database(commands.Cog):
  """Database Stuffs and Tings"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.loop = bot.loop
    self.columns = {
        "servers": [
            "id bigint PRIMARY KEY NOT NULL",
            "tier text NULL",
            "prefix varchar(5) NOT NULL DEFAULT '!'",
            "patreon_user bigint NULL DEFAULT NULL",
            "lang varchar(2) NULL DEFAULT NULL",
            "autodeletemsgs smallint NOT NULL DEFAULT 0",
            "max_mentions int NULL DEFAULT NULL",
            "max_messages text NULL",
            "remove_invites boolean DEFAULT false",
            "bot_manager text DEFAULT NULL",
            "persona text DEFAULT 'friday'",
            "customjoinleave text NULL",
            "botmasterrole text NULL DEFAULT NULL",
            "chatchannel text NULL DEFAULT NULL",
            "musicchannel text NULL DEFAULT NULL",
            "customsounds text NULL",
            r"roles json[] NOT NULL DEFAULT '{}'",
            r"text_channels json[] NOT NULL DEFAULT '{}'",
        ],
        "votes": [
            "id bigint PRIMARY KEY NOT NULL",
            "to_remind boolean NOT NULL DEFAULT false",
            "has_reminded boolean NOT NULL DEFAULT false",
            "voted_time timestamp NULL DEFAULT NULL"
        ],
        "countdowns": [
            "guild bigint NULL",
            "channel bigint NOT NULL",
            "message bigint NOT NULL",
            "title text NULL",
            "time bigint NOT NULL"
        ],
        "welcome": [
            "guild_id bigint PRIMARY KEY NOT NULL",
            "role_id text DEFAULT NULL",
            "channel_id text DEFAULT NULL",
            "message text DEFAULT NULL"
        ],
        "blacklist": [
            "id bigint",
            "guild_id bigint",
            "word text"
        ],
    }
    self.update_local_values.start()
    self.loop.run_until_complete(self.setup())
    if self.bot.cluster_idx == 0:
      self.loop.run_until_complete(self.create_tables())
      self.loop.run_until_complete(self.sync_table_columns())

  async def setup(self):
    hostname = 'localhost' if self.bot.prod or self.bot.canary else os.environ["DBHOSTNAME"]
    username = os.environ["DBUSERNAMECANARY"] if self.bot.canary else os.environ["DBUSERNAME"] if self.bot.prod else os.environ["DBUSERNAMELOCAL"]
    password = os.environ["DBPASSWORDCANARY"] if self.bot.canary else os.environ["DBPASSWORD"] if self.bot.prod else os.environ["DBPASSWORDLOCAL"]
    database = os.environ["DBDATABASECANARY"] if self.bot.canary else os.environ["DBDATABASE"] if self.bot.prod else os.environ["DBDATABASELOCAL"]
    self.connection: asyncpg.Pool = await asyncpg.create_pool(host=hostname, user=username, password=password, database=database, loop=self.loop)

  @commands.Cog.listener()
  async def on_ready(self):
    actual_guilds, checked_guilds = [guild.id for guild in self.bot.guilds], []
    for guild_id in await self.query("SELECT id FROM servers"):
      if int(guild_id[0]) in actual_guilds:
        checked_guilds.append(guild_id)
    if len(checked_guilds) == len(self.bot.guilds):
      self.bot.logger.info("All guilds are in the Database")

  @commands.Cog.listener()
  async def on_connect(self):
    #
    # FIXME: I think this could delete some of the db with more than one cluster
    #
    if self.bot.cluster_idx == 0:
      current = []
      for guild in self.bot.guilds:
        current.append(guild.id)
        roles = json.dumps([{"name": i.name, "id": i.id, "position": i.position} for i in guild.roles])
        if len(guild.roles) == 0:
          roles = json.dumps([{"name": i.name, "id": i.id, "position": i.position} for i in await guild.fetch_roles()])
        text_channels = json.dumps([{"name": i.name, "id": i.id, "type": str(i.type), "position": i.position} for i in guild.text_channels])
        if len(guild.text_channels) == 0:
          text_channels = json.dumps([{"name": i.name, "id": i.id, "type": str(i.type), "position": i.position} for i in await guild.fetch_channels() if str(i.type) == "text"])
        await self.query(f"""INSERT INTO servers (id,lang,roles,text_channels) VALUES ({guild.id},'{guild.preferred_locale.split('-')[0] if guild.preferred_locale is not None else 'en'}',array[$1]::json[],array[$2]::json[]) ON CONFLICT(id) DO UPDATE SET roles=array[$1]::json[], text_channels=array[$2]::json[]""", roles, text_channels)
      await self.query(f"DELETE FROM servers WHERE id NOT IN ({','.join([str(i) for i in current])})")

    for i, p in await self.query("SELECT id,prefix FROM servers"):
      self.bot.prefixes.update({int(i): str(p)})

  @commands.Cog.listener()
  async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
    if not isinstance(after, discord.TextChannel):
      return
    text_channels = json.dumps([{"name": i.name, "id": i.id, "type": str(i.type), "position": i.position} for i in after.guild.text_channels])
    await self.query("""UPDATE servers SET text_channels=array[$1]::json[] WHERE id=$2""", text_channels, after.guild.id)

  @commands.Cog.listener()
  async def on_guild_role_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
    roles = json.dumps([{"name": i.name, "id": i.id, "position": i.position} for i in after.guild.roles])
    await self.query("""UPDATE servers SET roles=array[$1]::json[] WHERE id=$2""", roles, after.guild.id)

  @tasks.loop(minutes=1)
  async def update_local_values(self):
    prefixes = {}
    for i, p in await self.query("SELECT id,prefix FROM servers"):
      prefixes.update({int(i): str(p)})

    self.bot.prefixes = prefixes

  @update_local_values.before_loop
  async def update_local_values_before(self):
    await self.bot.wait_until_ready()

  async def create_tables(self):
    for table in self.columns:
      await self.query(f"CREATE TABLE IF NOT EXISTS {table} ({','.join(self.columns[table])});")

  async def sync_table_columns(self):
    # https://stackoverflow.com/questions/9991043/how-can-i-test-if-a-column-exists-in-a-table-using-an-sql-statement
    for table in self.columns:
      for column in self.columns[table]:
        result = await self.query(f"SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='{table}' AND column_name='{column.split(' ')[0]}') LIMIT 1")
        if not result:
          await self.query(f"ALTER TABLE {table} ADD COLUMN {column};")

  async def query(self, query: str, *params) -> Union[str, None, list]:
    async with self.connection.acquire() as mycursor:
      if "select" in query.lower():
        result = await mycursor.fetch(query, *params)
      else:
        await mycursor.execute(query, *params)
    if hasattr(self.bot, "logger"):
      self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {params}")
    if "select" in query.lower():
      if isinstance(result, list) and len(result) == 1 and "limit 1" in query.lower():
        result = [tuple(i) for i in result][0]
        if len(result) == 1:
          return result[0]
        return result
      if isinstance(result, list) and len(result) > 0 and "limit 1" not in query.lower():
        return [tuple(i) for i in result]
      elif isinstance(result, list) and len(result) == 0 and "limit 1" in query.lower():
        return None
      return result

  def cog_unload(self):
    self.update_local_values.stop()


def setup(bot):
  bot.add_cog(Database(bot))
