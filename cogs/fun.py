from __future__ import annotations

import asyncio
import datetime
import json
import re
from collections import defaultdict
# import random
from typing import TYPE_CHECKING, Any, Optional, Sequence, List, Tuple
from typing_extensions import Annotated

import discord
import numpy as np
import numpy.random as random
from async_timeout import timeout
from discord.ext import commands, tasks
# sys.path.insert(1, os.path.join(sys.path[0], '..'))
from pyfiglet import figlet_format

from functions import MessageColors, checks, embed, exceptions
from functions.config import PremiumTiersNew

if TYPE_CHECKING:
  from functions.custom_contexts import GuildContext, MyContext
  from index import Friday


with open('./config.json') as f:
  config = json.load(f)


POLLNAME_REGEX = re.compile(r'(?:\s{4}|\t)(.+)')


def is_nacl_server():
  async def predicate(ctx: MyContext):
    if ctx.guild is None:
      raise commands.NotOwner()
    if ctx.guild.id not in (215346091321720832, 243159711237537802):
      raise commands.NotOwner()
    return True
  return commands.check(predicate)


class Fun(commands.Cog):
  """Fun games and other commands to give more life to your Discord server."""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot
    self.countdowns: list[tuple[str, str, str, Any, float]] = []
    self.rpsoptions = ["rock", "paper", "scissors"]
    self.countdown_messages = []
    self.loop_countdown.add_exception_type(discord.NotFound)
    # self.timeouter = None
    # self.timeoutCh = None

    self.poll_edit_batch = defaultdict(None)
    self.poll_edit_lock = asyncio.Lock(loop=bot.loop)

    self.callroulette_batch: List[Tuple[discord.Member, Sequence[discord.VoiceChannel]]] = []

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def cog_load(self) -> None:
    self.loop_countdown.start()
    self.poll_loop.start()
    countdowns = await self.bot.pool.fetch("SELECT guild,channel,message,title,time FROM countdowns")
    for countdown in countdowns:
      self.countdowns.append(tuple(c for c in countdown))
    if self.callroulette_loop.is_running():
      self.callroulette_loop.cancel()
    self.callroulette_loop.start()

  async def cog_unload(self):
    self.loop_countdown.stop()
    self.poll_loop.stop()
    self.callroulette_loop.stop()

  async def cog_command_error(self, ctx: MyContext, error: commands.CommandError):
    error = getattr(error, "original", error)
    just_send = (exceptions.ArgumentTooSmall, exceptions.ArgumentTooLarge)
    if isinstance(error, just_send):
      await ctx.send(embed=embed(title=f"{error}", color=MessageColors.error()))
    elif isinstance(error, asyncio.TimeoutError):
      await ctx.send(embed=embed(title="This command took too long to execute. Please try again with different arguments", color=MessageColors.error()))

  # @commands.Cog.listener()
  # async def on_ready(self):
  #   self.bot.add_view(views.StopButton())

  # TODO: has no way to end this command ATM
  # TODO: can only store one user total for all of friday
  # @commands.group(name="timeout",aliases=["banish"],description="Put someone into a voice channel for a timeout",invoke_without_command=True)
  # @commands.guild_only()
  # @commands.bot_has_guild_permissions(move_members = True)
  # @commands.has_guild_permissions(move_members = True)
  # @commands.bot_has_permissions(send_messages = True, read_messages = True, embed_links = True)
  # async def timeout(self,ctx,channel:discord.VoiceChannel,member:discord.Member):
  #   self.timeouter = member
  #   self.timeoutCh = channel
  #   try:
  #     await member.move_to(channel,reason=f"{ctx.author} called the move command")
  #   except:
  #     raise
  #   await ctx.channel.send(embed=embed(title=f"Successfully moved {member} to {channel}"))

  # @timeout.command(name="stop")
  # @commands.guild_only()
  # async def timeout_stop(self,ctx):
  #   print("")

  # @commands.Cog.listener()
  # async def on_voice_state_update(self,member,before,after):
  #   if before.channel == self.timeoutCh and member == self.timeouter:
  #     await member.move_to(self.timeoutCh,reason="Bad dog, stay in your timeout room")

  # @commands.command(name="crowdcontrol",aliases=["cc"],description="Sends every back to the channel they came from if they enter a specific voicechannel")
  # @commands.guild_only()
  # @commands.bot_has_guild_permissions(move_members = True)
  # @commands.bot_has_permissions(send_messages = True, read_messages = True, embed_links = True)
  # @commands.has_guild_permissions(move_members = True)

  @commands.command(name="rockpaperscissors", help="Play Rock Paper Scissors with Friday", aliases=["rps"], usage="<rock, paper or scissors>")
  async def norm_rockpaperscissors(self, ctx: MyContext, choice: str):
    arg = choice.lower()

    if arg not in self.rpsoptions:
      return await ctx.send(embed=embed(title=f"`{arg}` is not Rock, Paper, Scissors. Please choose one of those three.", color=MessageColors.error()))

    mychoice = random.choice(self.rpsoptions)

    if mychoice == arg:
      conclusion = "Draw"
    elif mychoice == "rock" and arg == "paper":
      conclusion = self.bot.user
    elif mychoice == "rock" and arg == "scissors":
      conclusion = self.bot.user
    elif mychoice == "paper" and arg == "scissors":
      conclusion = ctx.author
    elif mychoice == "paper" and arg == "rock":
      conclusion = ctx.author
    elif mychoice == "scissors" and arg == "rock":
      conclusion = ctx.author
    elif mychoice == "scissors" and arg == "paper":
      conclusion = self.bot.user
    else:
      conclusion = "Something went wrong"

    return await ctx.send(
        embed=embed(
            title=f"Your move: {arg} VS My move: {mychoice}",
            color=MessageColors.rps(),
            description=f"The winner of this round is: **{conclusion}**"))

  MINEEMOTES = {
      "X": "💥",
      0: "0️⃣",
      1: "1️⃣",
      2: "2️⃣",
      3: "3️⃣",
      4: "4️⃣",
      5: "5️⃣",
      6: "6️⃣",
      7: "7️⃣",
      8: "8️⃣",
      "0": "0️⃣",
      "1": "1️⃣",
      "2": "2️⃣",
      "3": "3️⃣",
      "4": "4️⃣",
      "5": "5️⃣",
      "6": "6️⃣",
      "7": "7️⃣",
      "8": "8️⃣"
  }

  @commands.command(name="minesweeper", aliases=["ms"], extras={"examples": ["9 10", "5 5"]}, help="Play minesweeper")
  async def norm_minesweeper(self, ctx, size: int = 5, bomb_count: int = 6):
    async with timeout(2):
      mines = await self.bot.loop.run_in_executor(None, self.mine_sweeper, size, bomb_count)
    await ctx.reply(embed=embed(title=f"{size}x{size} with {bomb_count} bombs", author_name="Minesweeper", description=mines))

  def mine_sweeper(self, size: int = 5, bomb_count: int = 3):
    if size > 9:
      raise commands.BadArgument("Size cannot be larger than 9 due to the message character limit of Discord")
    if bomb_count >= size**2 or bomb_count >= 81:
      raise commands.BadArgument("Bomb count cannot be larger than the game board")
    if size <= 1 or bomb_count <= 1:
      raise commands.BadArgument("Bomb count and board size must be greater than 1")

    arr = np.full((size, size), "0", dtype='<U21')

    # arr: list[list[str | int]] = [[0 for row in range(size)] for column in range(size)]

    planted, x = 0, 0
    while planted < bomb_count and x < size**2:
      x += 1
      loc = random.randint(0, size**2 - 1)
      row = loc // size
      col = loc % size

      if arr[row][col] == "X":
        continue

      arr[row][col] = "X"
      planted += 1

    for a in np.nditer(arr, op_flags=['readwrite']):
      if a == "X":
        continue

      neighbors = 0
      for row in range(max(0, int(a) - 1), min(size - 1, int(a) + 1) + 1):
        for col in range(max(0, int(a) - 1), min(size - 1, int(a) + 1) + 1):
          if a == row and a == col:
            continue
          if arr[row][col] == "X":
            neighbors += 1
      a[...] = neighbors

    return "||" + "||\n||".join("||||".join(self.MINEEMOTES[cell] for cell in row) for row in arr) + "||"

  @commands.command(name='souptime', help='Soup Time')
  @commands.cooldown(1, 7, commands.BucketType.user)
  async def norm_souptime(self, ctx: MyContext):
    await ctx.reply(embed=embed(
        title="Here is sum soup, just for you",
        color=MessageColors.souptime(),
        description="I hope you enjoy!",
        image=random.choice(config['soups'])
    ))

  @commands.command(name="coinflip", aliases=["coin"], help="Flip a coin")
  async def norm_coinflip(self, ctx: MyContext):
    await ctx.reply(embed=embed(title="The coin landed on: " + random.choice(["Heads", "Tails"])))

  # @cog_ext.cog_slash(
  #     name="coinflip",
  #     description="Flip a coin"
  # )
  # @checks.slash(user=False, private=True)
  # async def slash_coinflip(self, ctx):
  #   await ctx.send(embed=embed(title="The coin landed on: " + random.choice(["Heads", "Tails"])))

  # @commands.command(name="mostroles", description="Show the server members with the most roles")
  # async def norm_mostroles(self, ctx):
  #   # Requires members intent
  #   for member in ctx.guild.members:
  #     print(member)

  # @commands.command(name="secretsanta", aliases=["ss"], description="Secret Santa", hidden=True)
  # async def norm_secret_santa(self, ctx, members: commands.Greedy[discord.Member]):
  #   print("something")

  # @cog_ext.cog_slash(name="secretsanta", description="Secret Santa", options=[create_option("members", "The members of the secret santa", 6, True)], guild_ids=[243159711237537802, 707441352367013899])
  # async def slash_secret_santa(self, ctx, members):
  #   print("something")

  POLLEMOTES = {
      0: "1️⃣",
      1: "2️⃣",
      2: "3️⃣",
      3: "4️⃣",
      4: "5️⃣",
      5: "6️⃣",
      6: "7️⃣",
      7: "8️⃣",
      8: "9️⃣",
      9: "🔟"
  }

  def is_poll(self, msg: discord.Message) -> bool:
    e = msg.embeds[0]
    return bool(e.title and (e.title.startswith("Poll: ") or e.title.startswith("Pole: ")) and not (e.author and e.author.name and "Poll Ended" in e.author.name))

  @commands.group(name="poll", extras={"examples": ["\"this is a title\" '1' '2' '3'", "\"Do you like being pinged for random things\" Yes No \"I just mute everything\""]}, help="Make a poll. Contain each option in qoutes `'option' 'option 2'`", invoke_without_command=True, case_insensitive=True)
  # @commands.group(name="poll", extras={"examples": ["\"this is a title\" 1;;2;;3"]}, help="Make a poll. Seperate the options with `;;`")
  @commands.guild_only()
  @commands.bot_has_permissions(add_reactions=True)
  async def norm_poll(self, ctx: MyContext, title: str, option1: str = None, option2: str = None, option3: str = None, option4: str = None, option5: str = None, option6: str = None, option7: str = None, option8: str = None, option9: str = None, option10: str = None):
    options = []
    for item in [option1, option2, option3, option4, option5, option6, option7, option8, option9, option10]:
      if item is not None:
        options.append(item)

    if len(options) < 2:
      return await ctx.reply(embed=embed(title="Please choose 2 or more options for this poll", color=MessageColors.error()))

    await self.poll(ctx, title, options)

  def bar(self, iteration=0, total=0, length=25, decimals=1, fill="█"):
    percent = ("{0:." + str(decimals if iteration != total else 0) + "f}").format(100 * (iteration / float(max(total, 1))))
    filledLength = int(length * iteration // max(total, 1))
    bar = fill * filledLength + '░' * (length - filledLength)
    return f"\r |{bar}| {percent}% ({iteration}/{total})"

  async def poll(self, ctx: MyContext, title: str, options: Sequence[str]) -> None:
    x = 0
    titles = []
    vals = []
    ins = []
    for opt in options:
      titles.append(f"{self.POLLEMOTES[x]}\t{opt}")
      vals.append(f"{self.bar()}")
      ins.append(False)
      x += 1
    try:
      message = await ctx.send(embed=embed(title=f"Poll: {title}", fieldstitle=titles, fieldsval=vals, fieldsin=ins))
    except discord.HTTPException as e:
      raise e
    else:
      for x in range(len(options)):
        await message.add_reaction(self.POLLEMOTES[x])

  @tasks.loop(seconds=6.0)
  async def poll_loop(self):
    await self.bot.wait_until_ready()

    # FIXME: If there are too many polls being used in one channel, add some kind of lock for that
    async with self.poll_edit_lock:
      for msg in self.poll_edit_batch.values():
        available_reactions = [self.POLLEMOTES[x] for x in range(len(msg.embeds[0].fields))]
        voter_reactions = [x for x in msg.reactions if x.emoji in available_reactions]

        for item in available_reactions:
          if len([r for r in msg.reactions if r.emoji in self.POLLEMOTES.values()]) != len(available_reactions):
            await msg.add_reaction(item)

        react_count = sum(e.count - 1 for e in msg.reactions if e.emoji in available_reactions)

        titles, vals, ins = [], [], []
        for x, field in enumerate(msg.embeds[0].fields):
          t = POLLNAME_REGEX.findall(field.name)
          titles.append(f"{self.POLLEMOTES[x]}\t{t[0]}")
          ins.append(False)
          vals.append(self.bar(voter_reactions[x].count - 1 if len(voter_reactions) > x else 0, react_count))

        try:
          await msg.edit(embed=embed(title=msg.embeds[0].title.replace("Pole: ", "Poll: "), fieldstitle=titles, fieldsval=vals, fieldsin=ins))
        except discord.HTTPException:
          pass
      self.poll_edit_batch.clear()

  @commands.Cog.listener("on_raw_reaction_add")
  @commands.Cog.listener("on_raw_reaction_remove")
  async def on_raw_reaction(self, payload: discord.RawReactionActionEvent):
    if payload.member == self.bot.user:
      return
    if payload.emoji.name not in self.POLLEMOTES.values():
      return
    try:
      channel: Optional[discord.TextChannel] = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)  # type: ignore
      if not channel:
        return
      message = await channel.fetch_message(payload.message_id)
    except discord.HTTPException:
      pass
    else:
      if message is None or message.author != self.bot.user:
        return
      if len(message.embeds) == 0:
        return
      if not self.is_poll(message):
        return

      async with self.poll_edit_lock:
        self.poll_edit_batch[message.id] = message

  @norm_poll.command("title", hidden=True)
  @commands.guild_only()
  @commands.is_owner()
  async def poll_edit_title(self, ctx: MyContext, message: discord.Message, *, new_title: str):
    if not self.is_poll(message):
      return

    message.embeds[0].title = "Poll: " + new_title
    await message.edit(embed=message.embeds[0])
    await ctx.send(embed=embed(title="Poll Edited", description=f"The poll's title has been changed to `{new_title}`."))

  @norm_poll.command("option", aliases=["addoption"], hidden=True)
  @commands.guild_only()
  @commands.is_owner()
  @commands.bot_has_permissions(add_reactions=True)
  async def poll_edit_option(self, ctx: MyContext, message: discord.Message, option_id: int, *, new_name: str):
    if not self.is_poll(message):
      return

    if option_id <= 0 or option_id > 10:
      raise commands.BadArgument("Option ID must be between 1 and 10.")
    option_id = option_id - 1

    if not len(message.embeds[0].fields) > 1 or option_id > len(message.embeds[0].fields) - 1:
      message.embeds[0].add_field(name=f"{self.POLLEMOTES[option_id]}\t{new_name}", value=self.bar(0, 0), inline=False)
      await message.add_reaction(self.POLLEMOTES[option_id])
    else:
      message.embeds[0]._fields[option_id]["name"] = f"{self.POLLEMOTES[option_id]}\t{new_name}"

    await message.edit(embed=message.embeds[0])
    await ctx.send(embed=embed(title="Poll Edited", description=f"The poll's option `{option_id+1}` has been changed to `{new_name}`."))

  @norm_poll.command("remove", hidden=True)
  @commands.guild_only()
  @commands.is_owner()
  @commands.bot_has_permissions(add_reactions=True)
  async def poll_edit_remove(self, ctx: GuildContext, message: discord.Message, option_id: int):
    if not self.is_poll(message):
      return

    message.embeds[0].remove_field(option_id - 1)
    await message.edit(embed=message.embeds[0])
    await message.remove_reaction(self.POLLEMOTES[option_id - 1], ctx.guild.me)
    await ctx.send(embed=embed(title="Poll Edited", description=f"The poll's option `{option_id}` has been removed."))

  @norm_poll.command("conclude", aliases=["end", "finish"], hidden=True)
  @commands.guild_only()
  @commands.is_owner()
  async def poll_edit_conclude(self, ctx: MyContext, message: discord.Message):
    if not self.is_poll(message):
      return

    message.embeds[0].set_author(name="Poll Ended")
    await message.edit(embed=message.embeds[0])
    await ctx.send(embed=embed(title="Poll Ended", description="The poll has been concluded."))

  # @norm_poll.command(name="conclude", help="Concludes the poll", hidden=True)
  # @commands.guild_only()
  # @commands.bot_has_permissions(manage_messages=True)
  # async def norm_poll_conclude(self, ctx: MyContext, poll: discord.Message):
  #   if not self.is_poll(poll):
  #     return await ctx.send(embed=embed(title="That message is not a poll", color=MessageColors.error()))

  # @cog_ext.cog_subcommand(base="poll", base_desc="Make a poll", name="conclude", description="Concludes a poll", options=[create_option(name="message", description="The link to the poll message", option_type=SlashCommandOptionType.STRING, required=True)], guild_ids=[243159711237537802])
  # @checks.slash(user=True, private=False)
  # async def slash_poll_conclude(self, ctx: SlashContext, message: discord.Message):
  #   if not message.embeds[0].title.startswith("Poll: "):
  #     return await ctx.send(embed=embed(title="That message is not a poll", color=MessageColors.error()))

  def get_time(self, now: float, future: float) -> tuple[float, float, float]:
    time = datetime.timedelta(seconds=future - now)
    sec = time.seconds
    hours = sec // 3600
    minutes = (sec // 60) - (hours * 60)
    sec = sec % 60
    return hours, minutes, sec

  @commands.command(name="countdown", aliases=["cd"], help="Start a countdown. This command only updates every 10 seconds to avoid being ratelimited by Discord")
  @commands.max_concurrency(3, commands.BucketType.guild, wait=True)
  async def countdown(self, ctx: GuildContext, hours: int = 0, minutes: int = 0, seconds: int = 0, title: Optional[str] = None):
    if hours == 0 and minutes == 0 and seconds == 0:
      return await ctx.send_help(ctx.command)

    if hours < 0 or minutes < 0 or seconds < 0:
      return await ctx.reply(embed=embed(title="Only positive numbers are accepted", color=MessageColors.error()))

    current_countdowns = [item for item in self.countdowns if (item[0] is not None and item[0] == ctx.guild.id) or (item[0] is None and ctx.author.dm_channel is not None and item[1] == ctx.author.dm_channel.id)] if ctx.guild is not None else []
    free_max, paid_max = 3, 8
    if len(current_countdowns) > free_max:
      if ctx.guild is not None:
        guild_min = await checks.guild_is_min_tier(PremiumTiersNew.tier_1).predicate(ctx)
        if len(current_countdowns) > free_max and not guild_min:
          return await ctx.reply(embed=embed(title=f"This server can only have a max of {free_max} concurrent countdowns per server", description="To unlock more please check out [patreon.com/fridaybot](https://www.patreon.com/bePatron?u=42649008)", color=MessageColors.error()))
        elif len(current_countdowns) > paid_max and guild_min:
          return await ctx.reply(embed=embed(title=f"This server can only have a max of {paid_max} concurrent countdowns per server", color=MessageColors.error()))
      if ctx.guild is None and ctx.author.dm_channel is not None:
        user_min = await checks.user_is_min_tier(PremiumTiersNew.tier_1).predicate(ctx)
        if len(current_countdowns) > free_max and not user_min:
          return await ctx.reply(embed=embed(title=f"You can only have a max of {free_max} concurrent countdowns per server", description="To unlock more please check out [patreon.com/fridaybot](https://www.patreon.com/bePatron?u=42649008)", color=MessageColors.error()))
        elif len(current_countdowns) > paid_max and user_min:
          return await ctx.reply(embed=embed(title=f"You can only have a max of {paid_max} concurrent countdowns per server", color=MessageColors.error()))

    duration = datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)
    if duration.days > 0:
      return await ctx.reply(embed=embed(title="Countdowns can't be set to any longer than 24 hours", color=MessageColors.error()))
    now = datetime.datetime.utcnow().timestamp()
    future = now + duration.seconds
    hs, min, secs = self.get_time(now, future)
    message = await ctx.send(embed=embed(title=f"Countdown: {title if title is not None else ''}", description="```" + figlet_format(f"{hs}:{min}:{secs}") + "```"))
    await ctx.db.execute("INSERT INTO countdowns (guild,channel,message,title,time) VALUES ($1,$2,$3,$4,$5) ON CONFLICT DO NOTHING", str(message.guild.id), str(message.channel.id), str(message.id), title, future)  # type: ignore
    self.countdowns.append((str(ctx.guild.id), str(ctx.channel.id), str(message.id), title, future))
    self.countdown_messages.append((message, title, future))

  @tasks.loop(seconds=10.0)
  async def loop_countdown(self):
    if self.bot.is_closed():
      return
    x, y, batch, batch_delete_db = 0, 0, [], []
    if len(self.countdown_messages) == 0:
      for guild_id, channel_id, message_id, title, time in self.countdowns:
        try:
          channel = self.bot.get_channel(int(channel_id)) or await self.bot.fetch_channel(int(channel_id))
          message = channel and await channel.fetch_message(int(message_id))  # type: ignore
        except discord.NotFound:
          batch_delete_db.append(str(message_id))
          try:
            del self.countdown_messages[x]
          except Exception:
            pass
        else:
          self.countdown_messages.append((message, title, time))
        x += 1
    now = datetime.datetime.utcnow().timestamp()
    for message, title, time in self.countdown_messages:
      if time <= now:
        batch.append(message.edit(embed=embed(title=f"Countdown: {title if title is not None else ''}", description="```" + figlet_format("Done!") + "```")))
        batch_delete_db.append(str(message.id))
        del self.countdown_messages[y]
        del self.countdowns[y]
      else:
        hours, minutes, sec = self.get_time(now, time)
        batch.append(message.edit(embed=embed(title=f"Countdown: {title if title is not None else ''}", description="```" + figlet_format(f"{hours}:{minutes}:{sec}") + "```")))
      y += 1
    if len(batch_delete_db) > 0:
      batch.append(self.bot.pool.execute(f"""DELETE FROM countdowns WHERE message IN ('{"', '".join(batch_delete_db)}')"""))
    await asyncio.gather(*batch)

  @commands.Cog.listener()
  async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
    while self.bot.is_closed():
      await asyncio.sleep(0.1)
    if payload.guild_id is not None and len([item for item in self.countdowns if int(item[2]) == payload.message_id]) > 0:
      await self.bot.pool.execute("DELETE FROM countdowns WHERE message=$1", str(payload.message_id))
      self.countdown_messages.pop(self.countdown_messages.index([i for i in self.countdown_messages if int(i[0].id) == payload.message_id][0]))
      self.countdowns.pop(self.countdowns.index([i for i in self.countdowns if int(i[2]) == payload.message_id][0]))

  @loop_countdown.before_loop
  async def before_loop_countdown(self):
    await self.bot.wait_until_ready()

  # @commands.command("soup", help="Get a random soup picture")
  # async def soup(self, ctx: MyContext):
  #   redditlink = await self.bot.get_context(f"{ctx.clean_prefix}redditlink https://www.reddit.com/r/soup/random/.json")
  #   if not redditlink:
  #     return await ctx.send(embed=embed(title="This command not currently available. Please try again later."))

  #   await self.bot.invoke(redditlink)

  @commands.command("8ball", help="Ask the magic 8ball a question")
  async def eightball(self, ctx: MyContext, *, question: str):
    answers = [
        "It is certain.",
        "It is decidedly so.",
        "Without a doubt.",
        "Yes - definitely.",
        "You may rely on it.",
        "As I see it, yes.",
        "Most likely.",
        "Outlook good.",
        "Yes.",
        "Signs point to yes.",
        "Reply hazy, try again.",
        "Ask again later.",
        "Better not tell you now.",
        "Cannot predict now.",
        "Concentrate and ask again.",
        "Don't count on it.",
        "My reply is no.",
        "My sources say no.",
        "Outlook not so good.",
        "Very doubtful."
    ]

    await ctx.send(embed=embed(title=f"🎱 | {random.choice(answers)}"))

  @commands.command("rng", help="Get a random number between the given range")
  async def rng(self, ctx: MyContext, start: int = 0, end: int = 100):
    if start > end:
      return await ctx.send(embed=embed(title="Start cannot be greater than end", color=MessageColors.error()))
    try:
      number = random.randint(start, end)
    except ValueError as e:
      if str(e) == "high is out of bounds for int64":
        return await ctx.send(embed=embed(title="One or both of the numbers are too large", color=MessageColors.error()))
      elif str(e) == "low is out of bounds for int64":
        return await ctx.send(embed=embed(title="One or both of the numbers are too small", color=MessageColors.error()))
      else:
        return await ctx.send(embed=embed(title="(╯°□°）╯︵ ┻━┻", color=MessageColors.error()))
    else:
      await ctx.send(embed=embed(title=f"{number}"))

  @commands.command("choice", aliases=["pick", "select"], help="Pick a random item from a list. For multiple items, separate them with a comma.")
  async def choice(self, ctx: MyContext, *, choices: str):
    new_choices = choices.split(",")
    await ctx.send(embed=embed(title=f"{random.choice(new_choices)}"))

  @tasks.loop(seconds=2)
  async def callroulette_loop(self):
    if not self.callroulette_batch:
      return

    for member, excepts in self.callroulette_batch:
      all_channels = member.guild.voice_channels
      if not member.voice or not member.voice.channel or isinstance(member.voice.channel, discord.StageChannel):
        self.callroulette_batch.remove((member, excepts))
        continue
      for exp in excepts:
        if exp in excepts:
          all_channels.remove(exp)
      for ch in all_channels:
        perms = ch.permissions_for(member)
        if not perms.connect or not perms.view_channel:
          all_channels.remove(ch)
      index = all_channels.index(member.voice.channel) + 1
      if index >= len(all_channels):
        index = 0
      _next = all_channels[index]
      await member.move_to(_next, reason="Command: callroulette")
      if len(_next.members) > 1:
        self.callroulette_batch.remove((member, excepts))
        continue

  @commands.group("callroulette", aliases=["voiceroulette", "channelroulette"], invoke_without_command=True, case_insensitive=True, hidden=True)
  @commands.guild_only()
  @is_nacl_server()
  async def callroulette(self, ctx: GuildContext, excluded_channels: Annotated[List[discord.VoiceChannel], commands.Greedy[discord.VoiceChannel]] = []):
    """
      Auto ignores voicechannels that are currently occupied.
    """
    if ctx.author in [i for i, _ in self.callroulette_batch]:
      return await ctx.send(embed=embed(title="You already have callroulette active", color=MessageColors.error()))

    if not ctx.author.voice or not ctx.author.voice.channel:
      return await ctx.send(embed=embed(title="You are not in a voice channel", color=MessageColors.error()))

    self.callroulette_batch.append((ctx.author, excluded_channels))
    await ctx.send(embed=embed(title="Callroulette started"))

  @callroulette.command("stop", aliases=["end", "cancel"], hidden=True)
  @commands.guild_only()
  @is_nacl_server()
  async def callroulette_stop(self, ctx: GuildContext):
    if ctx.author not in [i for i, _ in self.callroulette_batch]:
      return await ctx.send(embed=embed(title="You do not have callroulette active", color=MessageColors.error()))

    excepts = self.callroulette_batch[self.callroulette_batch.index((ctx.author, []))][1]
    self.callroulette_batch.remove((ctx.author, excepts))
    await ctx.send(embed=embed(title="Callroulette stopped"))


async def setup(bot):
  await bot.add_cog(Fun(bot))
