import asyncio
import re
import time
import weakref
from typing import Optional

import asyncpg
import discord
from discord.ext import commands, tasks

from functions import MessageColors, cache, checks, embed, MyContext
from functions.formats import plural

# from .utils.paginator import SimplePages


class StarError(commands.CheckFailure):
  pass


def requires_starboard():
  async def predicate(ctx):
    if ctx.guild is None:
      return False

    cog = ctx.bot.get_cog('Stars')

    ctx.starboard = await cog.get_starboard(ctx.guild.id, connection=ctx.db)
    if ctx.starboard.channel is None:
      raise StarError('\N{WARNING SIGN} Starboard channel not found.')

    return True
  return commands.check(predicate)


class StarboardConfig:
  __slots__ = ('bot', 'id', 'channel_id', 'threshold', 'locked', 'needs_migration')

  def __init__(self, *, guild_id, bot, record=None):
    self.id = guild_id
    self.bot = bot

    if record:
      self.channel_id = record['channel_id']
      self.threshold = record['threshold']
      self.locked = record['locked']
      self.needs_migration = self.locked is None
      if self.needs_migration:
        self.locked = True

    else:
      self.channel_id = None

  @property
  def channel(self):
    guild = self.bot.get_guild(self.id)
    return guild and guild.get_channel(self.channel_id)


class Stars(commands.Cog):
  """A starboard to upvote posts obviously.

  There are two ways to make use of this feature, the first is
  via reactions, react to a message with \N{WHITE MEDIUM STAR} and
  the bot will automatically add (or remove) it to the starboard.

  The second way is via Developer Mode. Enable it under Settings >
  Appearance > Developer Mode and then you get access to Copy ID
  and using the star/unstar commands.
  """

  def __init__(self, bot):
    self.bot = bot

    # cache message objects to save Discord some HTTP requests.
    self._message_cache = {}
    self.clean_message_cache.start()

    # if it's in this set,
    self._about_to_be_deleted = set()

    self._locks = weakref.WeakValueDictionary()
    self.spoilers = re.compile(r'\|\|(.+?)\|\|')

  def cog_unload(self):
    self.clean_message_cache.cancel()

  async def cog_command_error(self, ctx, error):
    if isinstance(error, StarError):
      await ctx.send(embed=embed(title=error, color=MessageColors.ERROR))

  @tasks.loop(hours=1.0)
  async def clean_message_cache(self):
    self._message_cache.clear()

  @cache.cache()
  async def get_starboard(self, guild_id, *, connection=None):
    connection = connection or self.bot.pool
    query = "SELECT * FROM starboard WHERE id=$1;"
    record = await connection.fetchrow(query, guild_id)
    return StarboardConfig(guild_id=guild_id, bot=self.bot, record=record)

  def star_emoji(self, stars):
    if 5 > stars >= 0:
      return '\N{WHITE MEDIUM STAR}'
    elif 10 > stars >= 5:
      return '\N{GLOWING STAR}'
    elif 25 > stars >= 10:
      return '\N{DIZZY SYMBOL}'
    else:
      return '\N{SPARKLES}'

  def star_gradient_colour(self, stars):
    # We define as 13 stars to be 100% of the star gradient (half of the 26 emoji threshold)
    # So X / 13 will clamp to our percentage,
    # We start out with 0xfffdf7 for the beginning colour
    # Gradually evolving into 0xffc20c
    # rgb values are (255, 253, 247) -> (255, 194, 12)
    # To create the gradient, we use a linear interpolation formula
    # Which for reference is X = X_1 * p + X_2 * (1 - p)
    p = stars / 13
    if p > 1.0:
      p = 1.0

    red = 255
    green = int((194 * p) + (253 * (1 - p)))
    blue = int((12 * p) + (247 * (1 - p)))
    return (red << 16) + (green << 8) + blue

  def is_url_spoiler(self, text, url):
    spoilers = self.spoilers.findall(text)
    for spoiler in spoilers:
      if url in spoiler:
        return True
    return False

  def get_emoji_message(self, message, stars):
    emoji = self.star_emoji(stars)

    if stars > 1:
      content = f'{emoji} **{stars}** {message.channel.mention}'
    else:
      content = f'{emoji} {message.channel.mention}'

    embed = discord.Embed(description=message.content)
    embed.set_footer(text=message.id)
    if message.embeds:
      data = message.embeds[0]
      if data.type == 'image' and not self.is_url_spoiler(message.content, data.url):
        embed.set_image(url=data.url)

    if message.attachments:
      file = message.attachments[0]
      spoiler = file.is_spoiler()
      if not spoiler and file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
        embed.set_image(url=file.url)
      elif spoiler:
        embed.add_field(name='Attachment', value=f'||[{file.filename}]({file.url})||', inline=False)
      else:
        embed.add_field(name='Attachment', value=f'[{file.filename}]({file.url})', inline=False)

    ref = message.reference
    if ref and isinstance(ref.resolved, discord.Message):
      embed.add_field(name='Replying to...', value=f'[{ref.resolved.author}]({ref.resolved.jump_url})', inline=False)

    embed.add_field(name='Original', value=f'[Jump!]({message.jump_url})', inline=False)
    embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
    embed.timestamp = message.created_at
    embed.colour = self.star_gradient_colour(stars)
    return content, embed

  async def get_message(self, channel, message_id):
    try:
      return self._message_cache[message_id]
    except KeyError:
      try:
        o = discord.Object(id=message_id + 1)

        def pred(m):
          return m.id == message_id
        # don't wanna use get_message due to poor rate limit (1/1s) vs (50/1s)
        msg = await channel.history(limit=1, before=o).next()

        if msg.id != message_id:
          return None

        self._message_cache[message_id] = msg
        return msg
      except Exception:
        return None

  async def reaction_action(self, fmt, payload):
    if str(payload.emoji) != '\N{WHITE MEDIUM STAR}':
      return

    guild = self.bot.get_guild(payload.guild_id)
    if guild is None:
      return

    channel = guild.get_channel_or_thread(payload.channel_id)
    if not isinstance(channel, (discord.Thread, discord.TextChannel)):
      return

    method = getattr(self, f'{fmt}_message')

    user = payload.member or (await self.bot.get_or_fetch_member(guild, payload.user_id))
    if user is None or user.bot:
      return

    try:
      await method(channel, payload.message_id, payload.user_id, verify=True)
    except StarError:
      pass

  @commands.Cog.listener()
  async def on_guild_channel_delete(self, channel):
    if not isinstance(channel, discord.TextChannel):
      return

    starboard = await self.get_starboard(channel.guild.id)
    if starboard.channel is None or starboard.channel.id != channel.id:
      return

    # the starboard channel got deleted, so let's clear it from the database.
    async with self.bot.pool.acquire(timeout=300.0) as con:
      query = "DELETE FROM starboard WHERE id=$1;"
      await con.execute(query, channel.guild.id)

  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload):
    await self.reaction_action('star', payload)

  @commands.Cog.listener()
  async def on_raw_reaction_remove(self, payload):
    await self.reaction_action('unstar', payload)

  @commands.Cog.listener()
  async def on_raw_message_delete(self, payload):
    if payload.message_id in self._about_to_be_deleted:
      # we triggered this deletion ourselves and
      # we don't need to drop it from the database
      self._about_to_be_deleted.discard(payload.message_id)
      return

    starboard = await self.get_starboard(payload.guild_id)
    if starboard.channel is None or starboard.channel.id != payload.channel_id:
      return

    # at this point a message got deleted in the starboard
    # so just delete it from the database
    async with self.bot.pool.acquire(timeout=300.0) as con:
      query = "DELETE FROM starboard_entries WHERE bot_message_id=$1;"
      await con.execute(query, payload.message_id)

  @commands.Cog.listener()
  async def on_raw_bulk_message_delete(self, payload):
    if payload.message_ids <= self._about_to_be_deleted:
      # see comment above
      self._about_to_be_deleted.difference_update(payload.message_ids)
      return

    starboard = await self.get_starboard(payload.guild_id)
    if starboard.channel is None or starboard.channel.id != payload.channel_id:
      return

    async with self.bot.pool.acquire(timeout=300.0) as con:
      query = "DELETE FROM starboard_entries WHERE bot_message_id=ANY($1::bigint[]);"
      await con.execute(query, list(payload.message_ids))

  @commands.Cog.listener()
  async def on_raw_reaction_clear(self, payload):
    guild = self.bot.get_guild(payload.guild_id)
    if guild is None:
      return

    channel = guild.get_channel_or_thread(payload.channel_id)
    if channel is None or not isinstance(channel, (discord.Thread, discord.TextChannel)):
      return

    async with self.bot.pool.acquire(timeout=300.0) as con:
      starboard = await self.get_starboard(channel.guild.id, connection=con)
      if starboard.channel is None:
        return

      query = "DELETE FROM starboard_entries WHERE message_id=$1 RETURNING bot_message_id;"
      bot_message_id = await con.fetchrow(query, payload.message_id)

      if bot_message_id is None:
        return

      bot_message_id = bot_message_id[0]
      msg = await self.get_message(starboard.channel, bot_message_id)
      if msg is not None:
        await msg.delete()

  async def star_message(self, channel, message_id, starrer_id, *, verify=False):
    guild_id = channel.guild.id
    lock = self._locks.get(guild_id)
    if lock is None:
      self._locks[guild_id] = lock = asyncio.Lock(loop=self.bot.loop)

    async with lock:
      async with self.bot.pool.acquire(timeout=300.0) as con:
        if verify:
          log = self.bot.get_cog("Log")
          if log:
            conf = await log.get_guild_config(guild_id, connection=con)
            if "star" in conf.disabled_commands:
              return

        await self._star_message(channel, message_id, starrer_id, connection=con)

  async def _star_message(self, channel, message_id, starrer_id, *, connection):
    """Stars a message.

    Parameters
    ------------
    channel: :class:`TextChannel`
        The channel that the starred message belongs to.
    message_id: int
        The message ID of the message being starred.
    starrer_id: int
        The ID of the person who starred this message.
    connection: asyncpg.Connection
        The connection to use.
    """

    guild_id = channel.guild.id
    starboard = await self.get_starboard(guild_id)
    starboard_channel = starboard.channel
    if starboard_channel is None:
      raise StarError('\N{WARNING SIGN} Starboard channel not found.')

    if starboard.locked:
      raise StarError('\N{NO ENTRY SIGN} Starboard is locked.')

    if channel.is_nsfw() and not starboard_channel.is_nsfw():
      raise StarError('\N{NO ENTRY SIGN} Cannot star NSFW in non-NSFW starboard channel.')

    if channel.id == starboard_channel.id:
      # special case redirection code goes here
      # ergo, when we add a reaction from starboard we want it to star
      # the original message

      query = "SELECT channel_id, message_id FROM starboard_entries WHERE bot_message_id=$1;"
      record = await connection.fetchrow(query, message_id)
      if record is None:
        raise StarError('Could not find message in the starboard.')

      ch = channel.guild.get_channel_or_thread(record['channel_id'])
      if ch is None:
        raise StarError('Could not find original channel.')

      return await self._star_message(ch, record['message_id'], starrer_id, connection=connection)

    if not starboard_channel.permissions_for(starboard_channel.guild.me).send_messages:
      raise StarError('\N{NO ENTRY SIGN} Cannot post messages in starboard channel.')

    msg = await self.get_message(channel, message_id)

    if msg is None:
      raise StarError('\N{BLACK QUESTION MARK ORNAMENT} This message could not be found.')

    if msg.author.id == starrer_id:
      raise StarError('\N{NO ENTRY SIGN} You cannot star your own message.')

    empty_message = len(msg.content) == 0 and len(msg.attachments) == 0
    if empty_message or msg.type not in (discord.MessageType.default, discord.MessageType.reply):
      raise StarError('\N{NO ENTRY SIGN} This message cannot be starred.')

    # check if this is freshly starred
    # originally this was a single query but it seems
    # WHERE ... = (SELECT ... in some_cte) is bugged
    # so I'm going to do two queries instead
    query = """WITH to_insert AS (
                       INSERT INTO starboard_entries AS entries (message_id, channel_id, guild_id, author_id)
                       VALUES ($1, $2, $3, $4)
                       ON CONFLICT (message_id) DO NOTHING
                       RETURNING entries.id
                   )
                   INSERT INTO starrers (author_id, entry_id)
                   SELECT $5, entry.id
                   FROM (
                       SELECT id FROM to_insert
                       UNION ALL
                       SELECT id FROM starboard_entries WHERE message_id=$1
                       LIMIT 1
                   ) AS entry
                   RETURNING entry_id;
                """

    try:
      record = await connection.fetchrow(query, message_id, channel.id, guild_id, msg.author.id, starrer_id)
    except asyncpg.UniqueViolationError:
      raise StarError('\N{NO ENTRY SIGN} You already starred this message.')

    entry_id = record[0]

    query = "SELECT COUNT(*) FROM starrers WHERE entry_id=$1;"
    record = await connection.fetchrow(query, entry_id)

    count = record[0]
    if count < starboard.threshold:
      return

    # at this point, we either edit the message or we create a message
    # with our star info
    content, embed = self.get_emoji_message(msg, count)

    # get the message ID to edit:
    query = "SELECT bot_message_id FROM starboard_entries WHERE message_id=$1;"
    record = await connection.fetchrow(query, message_id)
    bot_message_id = record[0]

    if bot_message_id is None:
      new_msg = await starboard_channel.send(content, embed=embed)
      query = "UPDATE starboard_entries SET bot_message_id=$1 WHERE message_id=$2;"
      await connection.execute(query, new_msg.id, message_id)
    else:
      new_msg = await self.get_message(starboard_channel, bot_message_id)
      if new_msg is None:
        # deleted? might as well purge the data
        query = "DELETE FROM starboard_entries WHERE message_id=$1;"
        await connection.execute(query, message_id)
      else:
        await new_msg.edit(content=content, embed=embed)

  async def unstar_message(self, channel: discord.TextChannel, message_id, starrer_id, *, verify=False):
    guild_id = channel.guild.id
    lock = self._locks.get(guild_id)
    if lock is None:
      self._locks[guild_id] = lock = asyncio.Lock(loop=self.bot.loop)

    async with lock:
      async with self.bot.pool.acquire(timeout=300.0) as con:
        if verify:
          log = self.bot.get_cog("Log")
          if log:
            conf = await log.get_guild_config(guild_id, connection=con)
            if "star" in conf.disabled_commands:
              return
        await self._unstar_message(channel, message_id, starrer_id, connection=con)

  async def _unstar_message(self, channel, message_id, starrer_id, *, connection):
    """Unstars a message.

    Parameters
    ------------
    channel: :class:`TextChannel`
        The channel that the starred message belongs to.
    message_id: int
        The message ID of the message being unstarred.
    starrer_id: int
        The ID of the person who unstarred this message.
    connection: asyncpg.Connection
        The connection to use.
    """

    guild_id = channel.guild.id
    starboard = await self.get_starboard(guild_id)
    starboard_channel = starboard.channel
    if starboard_channel is None:
      raise StarError('\N{WARNING SIGN} Starboard channel not found.')

    if starboard.locked:
      raise StarError('\N{NO ENTRY SIGN} Starboard is locked.')

    if channel.id == starboard_channel.id:
      query = "SELECT channel_id, message_id FROM starboard_entries WHERE bot_message_id=$1;"
      record = await connection.fetchrow(query, message_id)
      if record is None:
        raise StarError('Could not find message in the starboard.')

      ch = channel.guild.get_channel_or_thread(record['channel_id'])
      if ch is None:
        raise StarError('Could not find original channel.')

      return await self._unstar_message(ch, record['message_id'], starrer_id, connection=connection)

    if not starboard_channel.permissions_for(starboard_channel.guild.me).send_messages:
      raise StarError('\N{NO ENTRY SIGN} Cannot edit messages in starboard channel.')

    query = """DELETE FROM starrers USING starboard_entries entry
                   WHERE entry.message_id=$1
                   AND   entry.id=starrers.entry_id
                   AND   starrers.author_id=$2
                   RETURNING starrers.entry_id, entry.bot_message_id
                """

    record = await connection.fetchrow(query, message_id, starrer_id)
    if record is None:
      raise StarError('\N{NO ENTRY SIGN} You have not starred this message.')

    entry_id = record[0]
    bot_message_id = record[1]

    query = "SELECT COUNT(*) FROM starrers WHERE entry_id=$1;"
    count = await connection.fetchrow(query, entry_id)
    count = count[0]

    if count == 0:
      # delete the entry if we have no more stars
      query = "DELETE FROM starboard_entries WHERE id=$1;"
      await connection.execute(query, entry_id)

    if bot_message_id is None:
      return

    bot_message = await self.get_message(starboard_channel, bot_message_id)
    if bot_message is None:
      return

    if count < starboard.threshold:
      self._about_to_be_deleted.add(bot_message_id)
      if count:
        # update the bot_message_id to be NULL in the table since we're deleting it
        query = "UPDATE starboard_entries SET bot_message_id=NULL WHERE id=$1;"
        await connection.execute(query, entry_id)

      await bot_message.delete()
    else:
      msg = await self.get_message(channel, message_id)
      if msg is None:
        raise StarError('\N{BLACK QUESTION MARK ORNAMENT} This message could not be found.')

      content, embed = self.get_emoji_message(msg, count)
      await bot_message.edit(content=content, embed=embed)

  @commands.group(invoke_without_command=True, case_insensitive=True, extras={"examples": ["starboard"]})
  @checks.is_admin()
  async def starboard(self, ctx, *, name: Optional[str] = 'starboard'):
    """Sets up the starboard for this server.

    This creates a new channel with the specified name
    and makes it into the server's "starboard". If no
    name is passed in then it defaults to "starboard".

    Choose wisely, this channel cannot be changed.
    """

    # bypass the cache just in case someone used the star
    # reaction earlier before having it set up, or they
    # decided to use the ?star command
    self.get_starboard.invalidate(self, ctx.guild.id)

    starboard = await self.get_starboard(ctx.guild.id, connection=ctx.db)
    if starboard.channel is not None:
      return await ctx.send(f"{starboard.channel.mention}", embed=embed(title='This server already has a starboard.'))

    if hasattr(starboard, 'locked'):
      try:
        confirm = await ctx.prompt('Apparently, a previously configured starboard channel was deleted. Is this true?')
      except RuntimeError as e:
        await ctx.send(embed=embed(title=e, color=MessageColors.ERROR))
      else:
        if confirm:
          await ctx.db.execute('DELETE FROM starboard WHERE id=$1;', ctx.guild.id)
        else:
          return await ctx.send(embed=embed(title='Aborting starboard creation. Join the bot support server for more questions.', color=MessageColors.ERROR))

    perms = ctx.channel.permissions_for(ctx.me)

    if not perms.manage_roles or not perms.manage_channels:
      raise commands.BotMissingPermissions(['manage_roles', 'manage_channels'])
      # return await ctx.send(embed=embed(title='\N{NO ENTRY SIGN} I do not have proper permissions (Manage Roles and Manage Channel)'))

    overwrites = {
        ctx.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True,
                                            embed_links=True, read_message_history=True),
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False,
                                                            create_public_threads=False, use_slash_commands=False,
                                                            read_message_history=True)
    }

    reason = f'{ctx.author} (ID: {ctx.author.id}) has created the starboard channel.'

    try:
      channel = await ctx.guild.create_text_channel(name=name, overwrites=overwrites, reason=reason)
    except discord.Forbidden:
      return await ctx.send(embed=embed(title='\N{NO ENTRY SIGN} I do not have permissions to create a channel.'))
    except discord.HTTPException:
      return await ctx.send(embed=embed(title='\N{NO ENTRY SIGN} This channel name is bad or an unknown error happened.'))

    query = "INSERT INTO starboard (id, channel_id) VALUES ($1, $2);"
    try:
      await ctx.db.execute(query, ctx.guild.id, channel.id)
    except BaseException:
      await channel.delete(reason='Failure to commit to create the ')
      await ctx.send(embed=embed(title='Could not create the channel due to an internal error. Join the bot support server for help.', color=MessageColors.ERROR))
    else:
      self.get_starboard.invalidate(self, ctx.guild.id)
      await ctx.send(f"{channel.mention}", embed=embed(title=f'\N{GLOWING STAR} Starboard created at `{channel}`.'))

  @starboard.command(name='info')
  @requires_starboard()
  async def starboard_info(self, ctx):
    """Shows meta information about the starboard."""
    starboard = ctx.starboard
    channel = starboard.channel
    data = []

    if channel is None:
      data.append('Channel: #deleted-channel')
    else:
      data.append(f'Channel: {channel.mention}')
      data.append(f'NSFW: {channel.is_nsfw()}')

    data.append(f'Locked: {starboard.locked}')
    data.append(f'Limit: {plural(starboard.threshold):star}')
    await ctx.send(embed=embed(title="Starboard Info", description='\n'.join(data)))

  @commands.group(invoke_without_command=True, ignore_extra=False, extras={"examples": ["707520808448294983", "https://discord.com/channels/707441352367013899/707458929696702525/707520808448294983"]})
  @commands.guild_only()
  async def star(self, ctx, message: discord.Message):
    """Stars a message via message ID.

    To star a message you should right click on the on a message and then
    click "Copy ID". You must have Developer Mode enabled to get that
    functionality.

    It is recommended that you react to a message with \N{WHITE MEDIUM STAR} instead.

    You can only star a message once.
    """

    try:
      await self.star_message(message.channel, message.id, ctx.author.id)
    except StarError as e:
      await ctx.send(embed=embed(title=e, color=MessageColors.ERROR))
    else:
      await ctx.message.delete()

  @commands.command(extras={"examples": ["707520808448294983", "https://discord.com/channels/707441352367013899/707458929696702525/707520808448294983"]})
  @commands.guild_only()
  async def unstar(self, ctx, message: discord.Message):
    """Unstars a message via message ID.

    To unstar a message you should right click on the on a message and then
    click "Copy ID". You must have Developer Mode enabled to get that
    functionality.
    """
    try:
      await self.unstar_message(message.channel, message.id, ctx.author.id, verify=True)
    except StarError as e:
      return await ctx.send(embed=embed(title=e, color=MessageColors.ERROR))
    else:
      await ctx.message.delete()

  @star.command(name='clean', extras={"examples": ["1", "3"]})
  @checks.is_admin()
  @requires_starboard()
  async def star_clean(self, ctx, stars: int = 1):
    """Cleans the starboard

    This removes messages in the starboard that only have less
    than or equal to the number of specified stars. This defaults to 1.

    Note that this only checks the last 100 messages in the starboard.

    This command requires the Manage Server permission.
    """

    stars = max(stars, 1)
    channel = ctx.starboard.channel

    last_messages = await channel.history(limit=100).map(lambda m: m.id).flatten()

    query = """WITH bad_entries AS (
                       SELECT entry_id
                       FROM starrers
                       INNER JOIN starboard_entries
                       ON starboard_entries.id = starrers.entry_id
                       WHERE starboard_entries.guild_id=$1
                       AND   starboard_entries.bot_message_id = ANY($2::bigint[])
                       GROUP BY entry_id
                       HAVING COUNT(*) <= $3
                   )
                   DELETE FROM starboard_entries USING bad_entries
                   WHERE starboard_entries.id = bad_entries.entry_id
                   RETURNING starboard_entries.bot_message_id
                """

    to_delete = await ctx.db.fetch(query, ctx.guild.id, last_messages, stars)

    # we cannot bulk delete entries over 14 days old
    min_snowflake = int((time.time() - 14 * 24 * 60 * 60) * 1000.0 - 1420070400000) << 22
    to_delete = [discord.Object(id=r[0]) for r in to_delete if r[0] > min_snowflake]

    try:
      self._about_to_be_deleted.update(o.id for o in to_delete)
      await channel.delete_messages(to_delete)
    except discord.HTTPException:
      await ctx.send(embed=embed(title='Could not delete messages.'))
    else:
      await ctx.send(embed=embed(title=f'\N{PUT LITTER IN ITS PLACE SYMBOL} Deleted {plural(len(to_delete)):message}.'))

  @star.command(name='show', extras={"examples": ["707520808448294983", "https://discord.com/channels/707441352367013899/707458929696702525/707520808448294983"]})
  @requires_starboard()
  async def star_show(self, ctx, message: discord.Message):
    """Shows a starred message via its ID.

    To get the ID of a message you should right click on the
    message and then click "Copy ID". You must have
    Developer Mode enabled to get that functionality.

    You can only use this command once per 10 seconds.
    """

    query = """SELECT entry.channel_id,
                          entry.message_id,
                          entry.bot_message_id,
                          COUNT(*) OVER(PARTITION BY entry_id) AS "Stars"
                   FROM starrers
                   INNER JOIN starboard_entries entry
                   ON entry.id = starrers.entry_id
                   WHERE entry.guild_id=$1
                   AND (entry.message_id=$2 OR entry.bot_message_id=$2)
                   LIMIT 1
                """

    record = await ctx.db.fetchrow(query, ctx.guild.id, message.id)
    if record is None:
      return await ctx.send(embed=embed(title='This message has not been starred.'))

    bot_message_id = record['bot_message_id']
    if bot_message_id is not None:
      # "fast" path, just redirect the message
      msg = await self.get_message(ctx.starboard.channel, bot_message_id)
      if msg is not None:
        e = msg.embeds[0] if msg.embeds else None
        return await ctx.send(msg.content, embed=e)
      else:
        # somehow it got deleted, so just delete the entry
        query = "DELETE FROM starboard_entries WHERE message_id=$1;"
        await ctx.db.execute(query, record['message_id'])
        return

    # slow path, try to fetch the content
    channel = ctx.guild.get_channel_or_thread(record['channel_id'])
    if channel is None:
      return await ctx.send(embed=embed(title="The message's channel has been deleted."))

    msg = await self.get_message(channel, record['message_id'])
    if msg is None:
      return await ctx.send(embed=embed(title='The message has been deleted.'))

    content, e = self.get_emoji_message(msg, record['Stars'])
    await ctx.send(content, embed=e)

  @star.command(name='migrate')
  @requires_starboard()
  @checks.is_admin()
  @commands.max_concurrency(1, commands.BucketType.guild)
  async def star_migrate(self, ctx):
    """Migrates the starboard to the newest version.

    While doing this, the starboard is locked.

    Note: This is an **incredibly expensive operation**.

    It will take a very long time.

    You must have Manage Server permissions to use this.
    """

    perms = ctx.starboard.channel.permissions_for(ctx.me)
    if not perms.read_message_history:
      return await ctx.send(f"{ctx.starboard.channel.mention}", embed=embed(title=f'Bot does not have Read Message History in `{ctx.starboard.channel}`.'))

    if ctx.starboard.locked:
      return await ctx.send(embed=embed(title='Starboard must be unlocked to migrate. It will be locked during the migration.'))

    stats = self.bot.get_cog('Stats')
    if stats is None:
      return await ctx.send(embed=embed(title='Internal error occurred: Stats cog not loaded'))

    webhook = stats.webhook

    start = time.time()
    guild_id = ctx.guild.id
    query = "UPDATE starboard SET locked=TRUE WHERE id=$1;"
    await ctx.db.execute(query, guild_id)
    self.get_starboard.invalidate(self, guild_id)

    await ctx.send(embed=embed(title='Starboard is now locked and migration will now begin.'))

    valid_msg = re.compile(r'.+?<#(?P<channel_id>[0-9]{17,21})>\s*ID\:\s*(?P<message_id>[0-9]{17,21})')
    async with ctx.typing():
      fetched = 0
      updated = 0
      failed = 0

      # At the time of writing, the average server only had ~256 entries.
      async for message in ctx.starboard.channel.history(limit=1000):
        fetched += 1

        match = valid_msg.match(message.content)
        if match is None:
          continue

        groups = match.groupdict()
        groups['guild_id'] = guild_id
        fmt = 'https://discord.com/channels/{guild_id}/{channel_id}/{message_id}'.format(**groups)
        if len(message.embeds) == 0:
          continue

        _embed = message.embeds[0]
        if len(embed.fields) == 0 or _embed.fields[0].name == 'Attachments':
          _embed.add_field(name='Original', value=f'[Jump!]({fmt})', inline=False)
          try:
            await message.edit(embed=_embed)
          except discord.HTTPException:
            failed += 1
          else:
            updated += 1

      delta = time.time() - start
      query = "UPDATE starboard SET locked = FALSE WHERE id=$1;"
      await ctx.db.execute(query, guild_id)
      self.get_starboard.invalidate(self, guild_id)

      m = await ctx.send(embed=embed(title='Migration complete!',
                                     description='The starboard has been unlocked.\n'
                                     f'Updated {updated}/{fetched} entries to the new format.\n'
                                     f'Took {delta:.2f}s.'))

      e = discord.Embed(title='Starboard Migration', colour=discord.Colour.gold())
      e.add_field(name='Updated', value=updated)
      e.add_field(name='Fetched', value=fetched)
      e.add_field(name='Failed', value=failed)
      e.add_field(name='Name', value=ctx.guild.name)
      e.add_field(name='ID', value=guild_id)
      e.set_footer(text=f'Took {delta:.2f}s to migrate')
      e.timestamp = m.created_at
      await webhook.send(embed=e)

  def records_to_value(self, records, fmt=None, default='None!'):
    if not records:
      return default

    emoji = 0x1f947  # :first_place:
    fmt = fmt or (lambda o: o)
    return '\n'.join(f'{chr(emoji + i)}: {fmt(r["ID"])} ({plural(r["Stars"]):star})'
                     for i, r in enumerate(records))

  async def star_guild_stats(self, ctx):
    e = discord.Embed(title='Server Starboard Stats')
    e.timestamp = ctx.starboard.channel.created_at
    e.set_footer(text='Adding stars since')

    # messages starred
    query = "SELECT COUNT(*) FROM starboard_entries WHERE guild_id=$1;"

    record = await ctx.db.fetchrow(query, ctx.guild.id)
    total_messages = record[0]

    # total stars given
    query = """SELECT COUNT(*)
                   FROM starrers
                   INNER JOIN starboard_entries entry
                   ON entry.id = starrers.entry_id
                   WHERE entry.guild_id=$1;
                """

    record = await ctx.db.fetchrow(query, ctx.guild.id)
    total_stars = record[0]

    e.description = f'{plural(total_messages):message} starred with a total of {total_stars} stars.'
    e.colour = discord.Colour.gold()

    # this big query fetches 3 things:
    # top 3 starred posts (Type 3)
    # top 3 most starred authors  (Type 1)
    # top 3 star givers (Type 2)

    query = """WITH t AS (
                       SELECT
                           entry.author_id AS entry_author_id,
                           starrers.author_id,
                           entry.bot_message_id
                       FROM starrers
                       INNER JOIN starboard_entries entry
                       ON entry.id = starrers.entry_id
                       WHERE entry.guild_id=$1
                   )
                   (
                       SELECT t.entry_author_id AS "ID", 1 AS "Type", COUNT(*) AS "Stars"
                       FROM t
                       WHERE t.entry_author_id IS NOT NULL
                       GROUP BY t.entry_author_id
                       ORDER BY "Stars" DESC
                       LIMIT 3
                   )
                   UNION ALL
                   (
                       SELECT t.author_id AS "ID", 2 AS "Type", COUNT(*) AS "Stars"
                       FROM t
                       GROUP BY t.author_id
                       ORDER BY "Stars" DESC
                       LIMIT 3
                   )
                   UNION ALL
                   (
                       SELECT t.bot_message_id AS "ID", 3 AS "Type", COUNT(*) AS "Stars"
                       FROM t
                       WHERE t.bot_message_id IS NOT NULL
                       GROUP BY t.bot_message_id
                       ORDER BY "Stars" DESC
                       LIMIT 3
                   );
                """

    records = await ctx.db.fetch(query, ctx.guild.id)
    starred_posts = [r for r in records if r['Type'] == 3]
    e.add_field(name='Top Starred Posts', value=self.records_to_value(starred_posts), inline=False)

    def to_mention(o):
      return f'<@{o}>'

    star_receivers = [r for r in records if r['Type'] == 1]
    value = self.records_to_value(star_receivers, to_mention, default='No one!')
    e.add_field(name='Top Star Receivers', value=value, inline=False)

    star_givers = [r for r in records if r['Type'] == 2]
    value = self.records_to_value(star_givers, to_mention, default='No one!')
    e.add_field(name='Top Star Givers', value=value, inline=False)

    await ctx.send(embed=e)

  async def star_member_stats(self, ctx, member):
    e = discord.Embed(colour=discord.Colour.gold())
    e.set_author(name=member.display_name, icon_url=member.display_avatar.url)

    # this query calculates
    # 1 - stars received,
    # 2 - stars given
    # The rest are the top 3 starred posts

    query = """WITH t AS (
                       SELECT entry.author_id AS entry_author_id,
                              starrers.author_id,
                              entry.message_id
                       FROM starrers
                       INNER JOIN starboard_entries entry
                       ON entry.id=starrers.entry_id
                       WHERE entry.guild_id=$1
                   )
                   (
                       SELECT '0'::bigint AS "ID", COUNT(*) AS "Stars"
                       FROM t
                       WHERE t.entry_author_id=$2
                   )
                   UNION ALL
                   (
                       SELECT '0'::bigint AS "ID", COUNT(*) AS "Stars"
                       FROM t
                       WHERE t.author_id=$2
                   )
                   UNION ALL
                   (
                       SELECT t.message_id AS "ID", COUNT(*) AS "Stars"
                       FROM t
                       WHERE t.entry_author_id=$2
                       GROUP BY t.message_id
                       ORDER BY "Stars" DESC
                       LIMIT 3
                   )
                """

    records = await ctx.db.fetch(query, ctx.guild.id, member.id)
    received = records[0]['Stars']
    given = records[1]['Stars']
    top_three = records[2:]

    # this query calculates how many of our messages were starred
    query = """SELECT COUNT(*) FROM starboard_entries WHERE guild_id=$1 AND author_id=$2;"""
    record = await ctx.db.fetchrow(query, ctx.guild.id, member.id)
    messages_starred = record[0]

    e.add_field(name='Messages Starred', value=messages_starred)
    e.add_field(name='Stars Received', value=received)
    e.add_field(name='Stars Given', value=given)

    e.add_field(name='Top Starred Posts', value=self.records_to_value(top_three), inline=False)

    await ctx.send(embed=e)

  @star.command(name='stats', extras={"examples": ["215227961048170496", "@Motostar"]})
  @requires_starboard()
  async def star_stats(self, ctx, *, member: Optional[discord.Member] = None):
    """Shows statistics on the starboard usage of the server or a member."""

    if member is None:
      await self.star_guild_stats(ctx)
    else:
      await self.star_member_stats(ctx, member)

  @star.command(name='random')
  @requires_starboard()
  async def star_random(self, ctx):
    """Shows a random starred message."""

    query = """SELECT bot_message_id
                   FROM starboard_entries
                   WHERE guild_id=$1
                   AND bot_message_id IS NOT NULL
                   OFFSET FLOOR(RANDOM() * (
                       SELECT COUNT(*)
                       FROM starboard_entries
                       WHERE guild_id=$1
                       AND bot_message_id IS NOT NULL
                   ))
                   LIMIT 1
                """

    record = await ctx.db.fetchrow(query, ctx.guild.id)

    if record is None:
      return await ctx.send('Could not find anything.')

    message_id = record[0]
    message = await self.get_message(ctx.starboard.channel, message_id)
    if message is None:
      return await ctx.send(f'Message {message_id} has been deleted somehow.')

    if message.embeds:
      await ctx.send(message.content, embed=message.embeds[0])
    else:
      await ctx.send(message.content)

  @star.command(name='lock')
  @checks.is_admin()
  @requires_starboard()
  async def star_lock(self, ctx):
    """Locks the starboard from being processed.

    This is a moderation tool that allows you to temporarily
    disable the starboard to aid in dealing with star spam.

    When the starboard is locked, no new entries are added to
    the starboard as the bot will no longer listen to reactions or
    star/unstar commands.

    To unlock the starboard, use the unlock subcommand.

    To use this command you need Manage Server permission.
    """

    if ctx.starboard.needs_migration:
      return await ctx.send(embed=embed(title='Your starboard requires migration!'))

    query = "UPDATE starboard SET locked=TRUE WHERE id=$1;"
    await ctx.db.execute(query, ctx.guild.id)
    self.get_starboard.invalidate(self, ctx.guild.id)

    await ctx.send(embed=embed(title='Starboard is now locked.'))

  @star.command(name='unlock')
  @checks.is_admin()
  @requires_starboard()
  async def star_unlock(self, ctx):
    """Unlocks the starboard for re-processing.

    To use this command you need Manage Server permission.
    """

    if ctx.starboard.needs_migration:
      return await ctx.send(embed=embed(title='Your starboard requires migration!'))

    query = "UPDATE starboard SET locked=FALSE WHERE id=$1;"
    await ctx.db.execute(query, ctx.guild.id)
    self.get_starboard.invalidate(self, ctx.guild.id)

    await ctx.send(embed=embed(title='Starboard is now unlocked.'))

  @star.command(name='limit', aliases=['threshold'], extras={"examples": ["3", "5"]})
  @checks.is_admin()
  @requires_starboard()
  async def star_limit(self, ctx, stars: int):
    """Sets the minimum number of stars required to show up.

    When this limit is set, messages must have this number
    or more to show up in the starboard channel.

    You cannot have a negative number and the maximum
    star limit you can set is 100.

    Note that messages that previously did not meet the
    limit but now do will still not show up in the starboard
    until starred again.

    You must have Manage Server permissions to use this.
    """

    if ctx.starboard.needs_migration:
      return await ctx.send('Your starboard requires migration!')

    stars = min(max(stars, 1), 100)
    query = "UPDATE starboard SET threshold=$2 WHERE id=$1;"
    await ctx.db.execute(query, ctx.guild.id, stars)
    self.get_starboard.invalidate(self, ctx.guild.id)

    await ctx.send(embed=embed(title=f'Messages now require {plural(stars):star} to show up in the starboard.'))

  @commands.command(hidden=True)
  @commands.is_owner()
  async def star_announce(self, ctx: "MyContext", *, message):
    """Announce stuff to every starboard."""
    query = "SELECT id, channel_id FROM starboard;"
    records = await ctx.db.fetch(query)
    await ctx.release()

    to_send = []
    for guild_id, channel_id in records:
      guild = self.bot.get_guild(guild_id)
      if guild:
        channel = guild.get_channel(channel_id)
        if channel and channel.permissions_for(guild.me).send_messages:
          to_send.append(channel)

    confirm = await ctx.prompt(f"You're about to send this to {len(to_send)} channels. Are you sure you want to do this?")
    if not confirm:
      return await ctx.send(embed=embed(title='Cancelled.'))

    await ctx.send(embed=embed(title=f'Preparing to send to {len(to_send)} channels (out of {len(records)}).'))

    success = 0
    start = time.time()
    for index, channel in enumerate(to_send):
      if index % 5 == 0:
        await asyncio.sleep(1)

      try:
        await channel.send(message)
      except BaseException:
        pass
      else:
        success += 1

    delta = time.time() - start
    await ctx.send(embed=embed(title=f'Successfully sent to {success} channels (out of {len(to_send)}) in {delta:.2f}s.'))


async def setup(bot):
  await bot.add_cog(Stars(bot))
