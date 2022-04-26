from __future__ import annotations

import asyncio
# import time
from collections import defaultdict
from typing import Dict, List, Optional, Union

import asyncpg
import discord
from asyncpg import Record
from discord.ext import commands, tasks
from typing_extensions import TYPE_CHECKING

from functions import MessageColors, MyContext, cache, embed, formats

if TYPE_CHECKING:
  from typing_extensions import Self

  from index import Friday as Bot


class ScheduledEvent(commands.Converter):
  async def convert(self, ctx: "MyContext", argument):
    if argument.isdigit():
      return discord.utils.find(lambda e: e.id == int(argument), ctx.guild.scheduled_events)

    argument = argument.lower().split("/")[-1]
    if not argument.isdigit():
      raise commands.BadArgument(f"{argument} is not a valid event id or url.")

    return discord.utils.find(lambda e: e.id == int(argument), ctx.guild.scheduled_events)


class Config:
  __slots__ = ("bot", "guild_id", "events")  # , "default_event_role_id")

  bot: Bot
  guild_id: int
  events: Dict[int, Dict[str, Union[int, List[int]]]]

  @classmethod
  async def from_records(cls, records: List[Record], bot: Bot) -> Self:
    self = cls()

    self.bot = bot
    self.guild_id = records[0]["guild_id"]

    # self.default_event_role_id: Optional[int] = records[0]["default_event_role_id"]
    self.events = {}
    if records[0]["event_id"]:
      for r in records:
        # if not r["event_id"]:
        #   self.default_role_id: int = r["role_id"]
        #   break
        self.events.update({r["event_id"]: {"role": r["role_id"], "subscribers": set(r["subscribers"] or [])}})

    return self

  @property
  def roles(self) -> List[int]:
    return [r["role"] for r in self.events.values()]

  def get_role(self, event_id: int) -> Optional[int]:
    return self.events.get(event_id, {}).get("role")

  # def get_role(self, event_id: int) -> int:
  #   return self._get_role(event_id) or self.default_event_role_id

  def get_subsribers(self, event_id: int) -> List[int]:
    return self.events.get(event_id, {}).get("subscribers", [])


class ScheduledEvents(commands.Cog):
  def __init__(self, bot: Bot):
    self.bot: Bot = bot

    # self._data_batch = defaultdict(lambda: defaultdict(list))
    self._data_batch = defaultdict(list)
    self._batch_lock = asyncio.Lock(loop=bot.loop)
    self.batch_updates.add_exception_type(asyncpg.PostgresConnectionError)

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def cog_check(self, ctx: "MyContext"):
    if ctx.guild is None:
      raise commands.NoPrivateMessage("This command can only be used within a guild")

    if await ctx.bot.is_owner(ctx.author):
      return True

    if not ctx.author.guild_permissions.manage_guild:
      raise commands.MissingPermissions(["manage_guild"])

    if self.bot.prod and ctx.guild.id != 215346091321720832:
      raise commands.NotOwner()
    return True

  async def cog_load(self):
    self.batch_updates.start()

  async def cog_unload(self):
    self.batch_updates.stop()

  async def bulk_insert(self):
    query = """INSERT INTO scheduledevents (guild_id, event_id, role_id, subscribers)
              SELECT x.guild_id, x.event_id, x.role_id, x.result_array
              FROM jsonb_to_recordset($1::jsonb)
                AS x(guild_id BIGINT, event_id BIGINT, role_id BIGINT, result_array BIGINT[])
              ON CONFLICT(event_id) DO UPDATE SET subscribers = (SELECT x.result_array
              FROM jsonb_to_recordset($1::jsonb)
                AS x(guild_id BIGINT, event_id BIGINT, role_id BIGINT, result_array BIGINT[]));"""

    if not self._data_batch:
      return

    final_data = []
    async with self.bot.pool.acquire(timeout=300.0) as conn:
      for guild_id, data in self._data_batch.items():
        config = await self.get_guild_config(guild_id, connection=conn)
        event_subscribers = defaultdict(list)
        for event_id, role_id, user_id, insertion in data:
          event_subscribers[event_id].append((role_id, (user_id, insertion)))

        for event_id, other in dict(event_subscribers).items():
          role_id, _ = other[0]
          subscribers = [a for _, a in other]
          as_set = set(config.get_subsribers(event_id))

          for member_id, insertion in subscribers:
            func = as_set.add if insertion else as_set.discard
            func(member_id)

          final_data.append({
              "guild_id": guild_id,
              "event_id": event_id,
              "role_id": role_id,
              "result_array": list(as_set)
          })

        self.get_guild_config.invalidate(self, guild_id)

      await conn.execute(query, final_data)
      self.bot.logger.info(f"Inserted {len(final_data)} scheduled events.")
      self._data_batch.clear()

  @tasks.loop(seconds=15.0)
  async def batch_updates(self):
    async with self._batch_lock:
      await self.bulk_insert()

  @cache.cache()
  async def get_guild_config(self, guild_id: int, *, connection=None) -> Optional[Config]:
    connection = connection or self.bot.pool
    query = """SELECT s.id::bigint as guild_id, e.event_id, e.role_id, e.subscribers
              FROM servers s
              LEFT OUTER JOIN scheduledevents e ON s.id::bigint = e.guild_id
              WHERE s.id::bigint=$1;"""
    records = await connection.fetch(query, guild_id)
    return records and await Config.from_records(records, self.bot)

  @commands.Cog.listener()
  async def on_ready(self):
    if self.bot.cluster_idx != 0:
      return

    query = """SELECT * FROM scheduledevents;"""
    self.bot.logger.error("#Continue working on the events thing")
    records = await self.bot.pool.fetch(query)
    to_remove = []
    for record in records:
      guild = self.bot.get_guild(record["guild_id"])
      if not guild:
        continue

      try:
        event = await guild.fetch_scheduled_event(record["event_id"])
        event_id = event.id
      except discord.NotFound:
        event_id = record["event_id"]
        pass
      else:
        if event and event.status not in (discord.EventStatus.completed, discord.EventStatus.cancelled):
          continue

      to_remove.append(event_id)

      role = [r for r in await guild.fetch_roles() if r == record["role_id"]]
      if not role:
        continue
      role = role[0]

      for i, member in enumerate(role.members):
        if i % 5 == 0:
          await asyncio.sleep(1)
        try:
          await member.remove_roles(role, reason="Scheduled event role deleted/ended")
        except discord.HTTPException:
          pass
    if to_remove:
      query = """DELETE FROM scheduledevents WHERE event_id=ANY($1);"""
      await self.bot.pool.execute(query, to_remove)
      self.bot.logger.info(f"Removed {len(to_remove)} scheduled events.")

  # @commands.Cog.listener()
  # async def on_scheduled_event_create(self, event: discord.ScheduledEvent):
  #   async with self.bot.pool.acquire(timeout=300.0) as conn:
  #     query = """SELECT default_event_role_id
  #               FROM servers
  #               WHERE id = $1;"""
  #     default_event_role_id = await conn.fetchval(query, str(event.guild.id))

  #     query = """INSERT INTO scheduledevents
  #               (guild_id, event_id, role_id)
  #               VALUES ($1, $2, $3)
  #               ON CONFLICT(event_id) DO NOTHING;"""
  #     await conn.execute(query, event.guild.id, event.id, default_event_role_id)

  @commands.Cog.listener()
  async def on_scheduled_event_user_add(self, event: discord.ScheduledEvent, user: discord.User):
    if self.bot.prod and event.guild.id != 215346091321720832:
      return
    config = await self.get_guild_config(event.guild.id)
    if not config:
      return

    member = await self.bot.get_or_fetch_member(event.guild, user.id)
    if not member:
      return

    role_id = config.get_role(event.id)
    if not role_id:
      return

    if not member._roles.has(role_id):
      await member.add_roles(discord.Object(id=role_id), reason="Interested in a scheduled event")
    async with self._batch_lock:
      self._data_batch[event.guild.id].append((event.id, role_id, user.id, True))

  @commands.Cog.listener()
  async def on_scheduled_event_user_remove(self, event: discord.ScheduledEvent, user: discord.User):
    if self.bot.prod and event.guild.id != 215346091321720832:
      return
    config = await self.get_guild_config(event.guild.id)
    if not config:
      return

    member = await self.bot.get_or_fetch_member(event.guild, user.id)
    if not member:
      return

    role_id = config.get_role(event.id)
    if not role_id:
      return

    if member._roles.has(role_id):
      await member.remove_roles(discord.Object(id=role_id), reason="No longer interested in a scheduled event")
    async with self._batch_lock:
      self._data_batch[event.guild.id].append((event.id, role_id, user.id, False))

  @commands.Cog.listener()
  async def on_scheduled_event_update(self, before: discord.ScheduledEvent, after: discord.ScheduledEvent):
    if self.bot.prod and before.guild.id != 215346091321720832:
      return
    if before.status == after.status:
      return

    config = await self.get_guild_config(after.guild.id)
    if not config:
      return

    stoped = (discord.EventStatus.completed, discord.EventStatus.cancelled)
    if not (before.status not in stoped and after.status in stoped):
      return

    role_id = config.get_role(before.id)
    if not role_id:
      return

    x = 0
    async for user in before.users(limit=None):
      if x % 5 == 0:
        await asyncio.sleep(1)
      member = await self.bot.get_or_fetch_member(after.guild, user.id)
      if member and member._roles.has(role_id):
        await member.remove_roles(discord.Object(id=role_id), reason="Scheduled event has ended")
        x += 1
    query = """DELETE FROM scheduledevents
              WHERE guild_id=$1 AND event_id=$2;"""
    await self.bot.pool.execute(query, after.guild.id, after.id)
    self.get_guild_config.invalidate(self, after.guild.id)
    self.bot.logger.info(f"Event role ended and removed from {x} users in {after.guild.name} ({after.guild.id})")

  @commands.Cog.listener()
  async def on_scheduled_event_delete(self, event: discord.ScheduledEvent):
    if self.bot.prod and event.guild.id != 215346091321720832:
      return
    config = await self.get_guild_config(event.guild.id)
    if not config:
      return

    role_id = config.get_role(event.id)
    if not role_id:
      return

    role = event.guild.get_role(role_id)
    if role and not role.is_assignable():
      return

    subscribers = config.get_subsribers(event.id)
    x = 0
    async for member in self.bot.resolve_member_ids(event.guild, subscribers):
      if x % 5 == 0:
        await asyncio.sleep(1)
      if member._roles.has(role_id):
        try:
          await member.remove_roles(discord.Object(id=role_id), reason="Event deleted")
        except discord.HTTPException:
          pass
        x += 1

    query = """DELETE FROM scheduledevents
              WHERE guild_id=$1 AND event_id=$2;"""
    await self.bot.pool.execute(query, event.guild.id, event.id)
    self.get_guild_config.invalidate(self, event.guild.id)
    self.bot.logger.info(f"Event role deleted and removed from {x} users in {event.guild.name} ({event.guild.id})")

  @commands.Cog.listener()
  async def on_guild_role_delete(self, role: discord.Role):
    if self.bot.prod and role.guild.id != 215346091321720832:
      return
    config = await self.get_guild_config(role.guild.id)
    if not config:
      return

    if role.id not in config.roles:
      return

    query = """DELETE FROM scheduledevents
              WHERE guild_id=$1 AND role_id=$2;"""
    await self.bot.pool.execute(query, role.guild.id, role.id)
    self.get_guild_config.invalidate(self, role.guild.id)

  @commands.group("eventroles", aliases=["eventrole"], invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.bot_has_guild_permissions(manage_roles=True)
  @commands.has_guild_permissions(manage_roles=True, manage_events=True)
  async def eventroles(self, ctx: "MyContext"):
    """Add roles to members that mark a scheduled event as interested"""
    config = await self.get_guild_config(ctx.guild.id)
    if not config:
      return await ctx.send(embed=embed(title="No event roles found", color=MessageColors.ERROR))

    guild_events = await ctx.guild.fetch_scheduled_events(with_counts=False)
    events = [e for e in guild_events if e.id in config.events]

    description = ""
    for e in events:
      description += f"[{e.name}]({e.url}) - <@&{config.get_role(e.id)}>\n"

    await ctx.send(embed=embed(title="Event Roles", description=description or "No eventroles found"))

  # @eventroles.group("default", invoke_without_command=True, case_insensitive=True)
  # @commands.guild_only()
  # @commands.bot_has_guild_permissions(manage_roles=True)
  # @commands.has_guild_permissions(manage_roles=True, manage_events=True)
  # async def eventroles_default(self, ctx: "MyContext", *, role: discord.Role = None):
  #   """Sets the default role to be assigned to members that mark a scheduled event as interested"""
  #   if role and not role.is_assignable():
  #     raise commands.BadArgument("I don't have permission to assign that role.")

  #   config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
  #   if config and not role:
  #     role_id = config.default_event_role_id
  #     return await ctx.send(embed=embed(title="Default Role", description=f"<@&{role_id}>" if role_id else "None"))

  #   # if config and role.id in config.event_role_ids.values():
  #   #   raise commands.BadArgument("This role is already in use for an event")

  #   query = """UPDATE servers
  #             SET default_event_role_id = $2
  #             WHERE id = $1"""
  #   await ctx.db.execute(query, str(ctx.guild.id), role.id if role else None)
  #   self.get_guild_config.invalidate(self, ctx.guild.id)
  #   await ctx.send(embed=embed(title="Default role added"))

  # @eventroles_default.command("clear")
  # @commands.guild_only()
  # @commands.bot_has_guild_permissions(manage_roles=True)
  # @commands.has_guild_permissions(manage_roles=True, manage_events=True)
  # @commands.max_concurrency(1, commands.BucketType.guild)
  # async def eventroles_default_clear(self, ctx: "MyContext"):
  #   """Clears the default role"""
  #   config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
  #   if not config or config.default_event_role_id is None:
  #     return await ctx.send(embed=embed(title="No default role has been set", color=MessageColors.ERROR))

  #   default_event_role_id = config.default_event_role_id
  #   query = """UPDATE servers
  #             SET default_event_role_id = NULL
  #             WHERE id = $1"""
  #   await ctx.db.execute(query, str(ctx.guild.id))
  #   self.get_guild_config.invalidate(self, ctx.guild.id)

  #   confirm = await ctx.prompt("Would you also like this role to be removed from all users?")
  #   if not confirm:
  #     return await ctx.send(embed=embed(title="Default role cleared"))

  #   await ctx.send(embed=embed(title="Default role cleared and removing default role from all users"))
  #   start = time.time()
  #   async with ctx.typing():
  #     fetched = 0
  #     updated = 0
  #     failed = 0

  #     query = """SELECT event_id
  #               FROM scheduledevents
  #               WHERE guild_id=$1::bigint AND role_id=$2"""
  #     event_ids = [r["event_id"] for r in await ctx.db.fetch(query, ctx.guild.id, default_event_role_id)]

  #     for event in await ctx.guild.fetch_scheduled_events():
  #       if event.id not in event_ids:
  #         break

  #       async for user in event.users(limit=None):
  #         fetched += 1
  #         if fetched % 5 == 0:
  #           await asyncio.sleep(1)

  #         member = await self.bot.get_or_fetch_member(ctx.guild, user.id)
  #         if member and member._roles.has(config.default_event_role_id):
  #           try:
  #             await member.remove_roles(discord.Object(id=config.default_event_role_id), reason="Default role removed")
  #           except discord.HTTPException:
  #             failed += 1
  #           else:
  #             updated += 1
  #   delta = time.time() - start
  #   query = """DELETE FROM scheduledevents
  #             WHERE guild_id=$1::bigint AND role_id=$2"""
  #   await ctx.db.execute(query, ctx.guild.id, default_event_role_id)
  #   self.get_guild_config.invalidate(self, ctx.guild.id)
  #   m = await ctx.send(embed=embed(title="Default role removed",
  #                                  description=f"{fetched} users fetched\n"
  #                                  f"Removed roles from {updated}/{failed} users\n"
  #                                  f"Took {delta:.2f} seconds"))

  #   stats = self.bot.get_cog("Stats")
  #   self.bot.logger.info(f"Removed events roles from Guild: {ctx.guild.id} ({ctx.guild.name}) Members: {fetched} {updated}/{failed} Took: {delta:.2f}")
  #   if not stats:
  #     return
  #   await stats.webhook.send(embed=embed(title="Removed events roles",
  #                                        fieldstitle=["Updated", "Total", "Failed", "Name", "ID"],
  #                                        fieldsval=[updated, fetched, failed, ctx.guild.name, ctx.guild.id],
  #                                        footer=f"Took {delta:.2f} seconds",
  #                                        timestamp=m.created_at))

  @eventroles.command("set", aliases=["add"])
  @commands.guild_only()
  @commands.bot_has_guild_permissions(manage_roles=True)
  @commands.has_guild_permissions(manage_roles=True, manage_events=True)
  @commands.max_concurrency(1, commands.BucketType.guild)
  async def eventroles_add(self, ctx: "MyContext", event: Union[ScheduledEvent, discord.Invite], role: discord.Role = None):
    """Adds the given role to members that mark the given event as interested.

      Doesn't add any other roles for this event
    """
    if not event:
      raise commands.BadArgument("Failed to find event")

    if role and not role.is_assignable():
      raise commands.BadArgument("I don't have permission to assign that role.")

    if isinstance(event, discord.Invite):
      if not event.scheduled_event:
        raise commands.BadArgument("This invite is not associated with an event")
      event = event.scheduled_event

    async with self._batch_lock:
      await self.bulk_insert()

    config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
    if config and not role:
      role_id = config.get_role(event.id)
      return await ctx.send(embed=embed(title="Event Role", description=f"<@&{role_id}>" if role_id else "No role found"))

    if config and role.id == config.get_role(event.id):
      raise commands.BadArgument("This role is already in use for this event")

    if config and role.id in config.roles:
      raise commands.BadArgument("This role is already in use for another event")

    subscribers = []
    confirm = await ctx.prompt("This will change the roles of all members that are currently subscribed to this event. Are you sure you want to continue?")
    if not confirm:
      return await ctx.send(embed=embed(title="Cancelled"))

    async with ctx.typing():
      n = 0
      async for user in event.users(limit=None):
        member = await self.bot.get_or_fetch_member(ctx.guild, user.id)
        if not member:
          continue
        if n % 5 == 0:
          await asyncio.sleep(1)
        subscribers.append(member.id)

        if isinstance(member, discord.Member):
          if config.get_role(event.id) and member._roles.has(config.get_role(event.id)):
            await member.remove_roles(discord.Object(id=config.get_role(event.id)), reason="Old Event role")
          if not member._roles.has(role.id):
            await member.add_roles(role, reason="Event role")
        n += 1

    query = """INSERT INTO scheduledevents
              (guild_id, event_id, role_id, subscribers)
              VALUES ($1, $2, $3, $4)
              ON CONFLICT ON CONSTRAINT scheduledevents_event_id_key
              DO UPDATE SET role_id=$3, subscribers=$4;"""
    await ctx.db.execute(query, ctx.guild.id, event.id, role.id, subscribers)
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.send(embed=embed(title="Events role set", description=f"<@&{role.id}> and added to {formats.plural(len(subscribers)):user}"))

  @eventroles.command("clear", aliases=["remove", "delete"])
  @commands.guild_only()
  @commands.bot_has_guild_permissions(manage_roles=True)
  @commands.has_guild_permissions(manage_roles=True, manage_events=True)
  @commands.max_concurrency(1, commands.BucketType.guild)
  async def eventroles_clear(self, ctx: "MyContext", *, event_or_role: Union[ScheduledEvent, discord.Invite, discord.Role]):
    """Removes the given role from members that mark the given event as interested.

      Doesn't remove any other roles for this event
    """
    async with self._batch_lock:
      await self.bulk_insert()

    config = await self.get_guild_config(ctx.guild.id, connection=ctx.db)
    if not config:
      return await ctx.send(embed=embed(title="This server has not events setup", color=MessageColors.ERROR))

    if isinstance(event_or_role, discord.Invite):
      if not event_or_role.scheduled_event:
        raise commands.BadArgument("This invite is not associated with an event")
      event_or_role = event_or_role.scheduled_event

    if isinstance(event_or_role, discord.Role):
      removed = 0
      failed = 0
      if not event_or_role.is_assignable():
        raise commands.BadArgument("I don't have permission to assign that role.")

      if event_or_role.id not in config.roles:
        raise commands.BadArgument("This role is not in use")

      async with ctx.typing():
        for x, member in enumerate(event_or_role.members):
          if x % 5 == 0:
            await asyncio.sleep(1)
          try:
            await member.remove_roles(event_or_role, reason="Event role removed")
          except discord.HTTPException:
            failed += 1
          else:
            removed += 1
      query = """DELETE FROM scheduledevents
                WHERE guild_id=$1::bigint AND role_id=$2"""
      await ctx.db.execute(query, ctx.guild.id, event_or_role.id)
      self.get_guild_config.invalidate(self, ctx.guild.id)
      await ctx.send(embed=embed(title=f"Event role removed from {removed}/{len(event_or_role.members)} members"))
    else:
      if event_or_role.id not in config.events:
        raise commands.BadArgument("This event is not in use")

      if event_or_role.id not in config.roles:
        raise commands.BadArgument("This event has no role")

      role = ctx.guild.get_role(config.get_role(event_or_role.id)) or [r for r in await ctx.guild.fetch_roles() if r.id == config.get_role(event_or_role.id)][0]
      if not role:
        raise commands.BadArgument("This event has no role")

      removed = 0
      failed = 0
      async with ctx.typing():
        for x, member in enumerate(role.members):
          if x % 5 == 0:
            await asyncio.sleep(1)
          try:
            await member.remove_roles(role, reason="Event role removed")
          except discord.HTTPException:
            failed += 1
          else:
            removed += 1
          x += 1
      query = """DELETE FROM scheduledevents
                WHERE guild_id=$1::bigint AND event_id=$2"""
      await ctx.db.execute(query, ctx.guild.id, event_or_role.id)
      self.get_guild_config.invalidate(self, ctx.guild.id)
      await ctx.send(embed=embed(title=f"Event role removed from {removed}/{failed} members"))


async def setup(bot):
  await bot.add_cog(ScheduledEvents(bot))
