from __future__ import annotations

import asyncio
import json
import re
from collections import defaultdict
from enum import Enum
# import random
from typing import TYPE_CHECKING, List, Sequence, Tuple, Optional

import discord
import numpy as np
import numpy.random as random
from async_timeout import timeout
from discord.ext import commands, tasks
# sys.path.insert(1, os.path.join(sys.path[0], '..'))
from typing_extensions import Annotated

from functions import MessageColors, embed, exceptions

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


class RockPaperScissorsOptions(Enum):
  Rock = "rock"
  Paper = "paper"
  Scissors = "scissors"


class Fun(commands.Cog):
  """Fun games and other commands to give more life to your Discord server."""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot
    self.rpsoptions = ["rock", "paper", "scissors"]
    # self.timeouter = None
    # self.timeoutCh = None

    self.poll_edit_batch = defaultdict(None)
    self.poll_edit_lock = asyncio.Lock()

    self.callroulette_batch: List[Tuple[discord.Member, Sequence[discord.VoiceChannel]]] = []

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def cog_load(self) -> None:
    self.poll_loop.start()
    if self.callroulette_loop.is_running():
      self.callroulette_loop.cancel()
    self.callroulette_loop.start()

  async def cog_unload(self):
    self.poll_loop.stop()
    self.callroulette_loop.stop()

  async def cog_command_error(self, ctx: MyContext, error: commands.CommandError):
    error = getattr(error, "original", error)
    just_send = (exceptions.ArgumentTooSmall, exceptions.ArgumentTooLarge)
    if isinstance(error, just_send):
      await ctx.send(embed=embed(title=f"{error}", color=MessageColors.error()))
    elif isinstance(error, asyncio.TimeoutError):
      await ctx.send(embed=embed(title="This command took too long to execute. Please try again with different arguments", color=MessageColors.error()))

  @commands.hybrid_command(name="rockpaperscissors", aliases=["rps"], usage="<rock, paper or scissors>")
  async def rockpaperscissors(self, ctx: MyContext, choice: RockPaperScissorsOptions):
    """Play Rock Paper Scissors with Friday"""
    mychoice = RockPaperScissorsOptions(random.choice(self.rpsoptions))

    if mychoice == choice:
      conclusion = ctx.lang.fun.rockpaperscissors.win_options.draw
    elif mychoice == RockPaperScissorsOptions.Rock and choice == RockPaperScissorsOptions.Paper:
      conclusion = ctx.author.mention
    elif mychoice == RockPaperScissorsOptions.Paper and choice == RockPaperScissorsOptions.Scissors:
      conclusion = ctx.author.mention
    elif mychoice == RockPaperScissorsOptions.Scissors and choice == RockPaperScissorsOptions.Rock:
      conclusion = ctx.author.mention
    else:
      conclusion = self.bot.user.mention

    user_choice = ctx.lang.fun.rockpaperscissors.choices[choice.value]
    bot_choice = ctx.lang.fun.rockpaperscissors.choices[mychoice.value]
    return await ctx.send(
        embed=embed(
            title=ctx.lang.fun.rockpaperscissors.response_title.format(user_choice=user_choice, bot_choice=bot_choice),
            color=MessageColors.rps(),
            description=ctx.lang.fun.rockpaperscissors.response_description.format(winner_user_name=conclusion)))

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

  @commands.hybrid_command(aliases=["ms"], extras={"examples": ["9 10", "5 5"]})
  async def minesweeper(self, ctx: MyContext, size: int = 5, bomb_count: int = 6):
    """Play minesweeper"""
    if size > 9:
      raise commands.BadArgument(ctx.lang.fun.minesweeper.error_max_board_size)
    if bomb_count >= size**2 or bomb_count >= 81:
      raise commands.BadArgument(ctx.lang.fun.minesweeper.error_greater_than_board)
    if size <= 1 or bomb_count <= 1:
      raise commands.BadArgument(ctx.lang.fun.minesweeper.error_greater_than_one)

    async with timeout(2):
      mines = await self.bot.loop.run_in_executor(None, self.mine_sweeper, size, bomb_count)
    await ctx.reply(embed=embed(title=ctx.lang.fun.minesweeper.response_title.format(size=size, bomb_count=bomb_count), author_name=ctx.lang.fun.minesweeper.response_author, description=mines))

  def mine_sweeper(self, board_size: int, bomb_count: int) -> str:
    board = np.zeros((board_size, board_size), dtype=int)
    bomb_positions = np.random.choice(board_size * board_size, size=bomb_count, replace=False)
    board.flat[bomb_positions] = -1

    for i in range(board_size):
      for j in range(board_size):
        if board[i, j] == -1:
          continue
        n = 0
        for ni in [-1, 0, 1]:
          for nj in [-1, 0, 1]:
            if ni == 0 and nj == 0:
              continue
            if i + ni >= 0 and i + ni < board_size and j + nj >= 0 and j + nj < board_size:
              if board[i + ni, j + nj] == -1:
                n += 1
        board[i, j] = n

    board_str = ""
    for i in range(board_size):
      for j in range(board_size):
        if board[i, j] == -1:
          board_str += "||" + self.MINEEMOTES["X"] + "||"
        else:
          board_str += "||" + self.MINEEMOTES[board[i, j]] + "||"
      board_str += "\n"

    return board_str.strip()

  @commands.command(name='souptime')
  @commands.cooldown(1, 7, commands.BucketType.user)
  async def souptime(self, ctx: MyContext):
    """Soup Time"""
    await ctx.reply(embed=embed(
        title="Here is sum soup, just for you",
        color=MessageColors.souptime(),
        description="I hope you enjoy!",
        image=random.choice(config['soups'])
    ))

  @commands.command(name="coinflip", aliases=["coin"])
  async def coinflip(self, ctx: MyContext):
    """Flip a coin"""
    await ctx.reply(embed=embed(title="The coin landed on: " + random.choice(["Heads", "Tails"])))

  # @cog_ext.cog_slash(
  #     name="coinflip",
  #     description="Flip a coin"
  # )
  # @checks.slash(user=False, private=True)
  # async def slash_coinflip(self, ctx):
  #   await ctx.send(embed=embed(title="The coin landed on: " + random.choice(["Heads", "Tails"])))

  # @commands.command(name="mostroles", description="Show the server members with the most roles")
  # async def mostroles(self, ctx):
  #   # Requires members intent
  #   for member in ctx.guild.members:
  #     print(member)

  # @commands.command(name="secretsanta", aliases=["ss"], description="Secret Santa", hidden=True)
  # async def secret_santa(self, ctx, members: commands.Greedy[discord.Member]):
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

  # @commands.command("soup", help="Get a random soup picture")
  # async def soup(self, ctx: MyContext):
  #   redditlink = await self.bot.get_context(f"{ctx.clean_prefix}redditlink https://www.reddit.com/r/soup/random/.json")
  #   if not redditlink:
  #     return await ctx.send(embed=embed(title="This command not currently available. Please try again later."))

  #   await self.bot.invoke(redditlink)

  @commands.command("8ball")
  async def eightball(self, ctx: MyContext, *, question: str):
    """Ask the magic 8ball a question"""
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

  @commands.command("rng")
  async def rng(self, ctx: MyContext, start: int = 0, end: int = 100):
    """Get a random number between the given range"""
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

  @commands.command("choice", aliases=["pick", "select"])
  async def choice(self, ctx: MyContext, *, choices: str):
    """Pick a random item from a list. For multiple items, separate them with a comma."""
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
    """Auto ignores voicechannels that are currently occupied."""
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
