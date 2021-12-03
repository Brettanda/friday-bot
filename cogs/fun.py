import json
# import random
from typing import Optional
import numpy.random as random
import asyncio
import datetime
from async_timeout import timeout

import discord
from discord.ext import commands, tasks
# from discord_slash import cog_ext, SlashContext
# from discord_slash.utils.manage_commands import create_choice, create_option, SlashCommandOptionType

# sys.path.insert(1, os.path.join(sys.path[0], '..'))
from pyfiglet import figlet_format
from functions import MessageColors, embed, exceptions, checks
from typing_extensions import TYPE_CHECKING
from functions import MyContext

if TYPE_CHECKING:
  from index import Friday as Bot


with open('./config.json') as f:
  config = json.load(f)


class Fun(commands.Cog):
  """Fun games and other commands to give more life to your Discord server."""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.rpsoptions = ["rock", "paper", "scissors"]
    # self.timeouter = None
    # self.timeoutCh = None

  def __repr__(self):
    return "<cogs.Fun>"

  async def cog_command_error(self, ctx: "MyContext", error: Exception):
    error = getattr(error, "original", error)
    just_send = (exceptions.ArgumentTooSmall, exceptions.ArgumentTooLarge,)
    if isinstance(error, just_send):
      await ctx.send(embed=embed(title=f"{error}", color=MessageColors.ERROR))
    elif isinstance(error, asyncio.TimeoutError):
      await ctx.send(embed=embed(title="This command took too long to execute. Please try again.", color=MessageColors.ERROR))

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
  async def norm_rockpaperscissors(self, ctx: "MyContext", choice: str):
    await self.rock_paper_scissors(ctx, choice)

  # @cog_ext.cog_slash(
  #     name="rockpaperscissors",
  #     options=[
  #         create_option(
  #             "choice",
  #             description="Rock Paper or Scissors",
  #             option_type=3,
  #             required=True,
  #             choices=[
  #                 create_choice(
  #                     "rock",
  #                     "Rock"
  #                 ),
  #                 create_choice(
  #                     "paper",
  #                     "Paper"
  #                 ),
  #                 create_choice(
  #                     "scissors",
  #                     "Scissors"
  #                 )
  #             ]
  #         )
  #     ]
  # )
  # @checks.slash(user=False, private=True)
  # async def slash_rockpaperscissors(self, ctx, choice: str):
  #   await ctx.defer()
  #   await self.rock_paper_scissors(ctx, choice)

  # , SlashContext
  async def rock_paper_scissors(self, ctx: "MyContext", args: str) -> None:
    arg = args.lower()

    if arg not in self.rpsoptions:
      return await ctx.send(embed=embed(title=f"`{arg}` is not Rock, Paper, Scissors. Please choose one of those three.", color=MessageColors.ERROR))

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

    return await ctx.send(
        embed=embed(
            title=f"Your move: {arg} VS My move: {mychoice}",
            color=MessageColors.RPS,
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
      8: "8️⃣"
  }

  @commands.command(name="minesweeper", aliases=["ms"], help="Play minesweeper")
  async def norm_minesweeper(self, ctx, size: Optional[int] = 5, bomb_count: Optional[int] = 6):
    await ctx.reply(**await self.mine_sweeper(size, bomb_count))

  # @cog_ext.cog_slash(
  #     name="minesweeper",
  #     description="Minesweeper",
  #     options=[
  #         create_option("size", "SizeXSize", SlashCommandOptionType.INTEGER, False),
  #         create_option("bomb_count", "Amount of bombs", SlashCommandOptionType.INTEGER, False)
  #     ]
  # )
  # @checks.slash(user=False, private=True)
  # async def slash_minesweeper(self, ctx, size: int = 5, bomb_count: int = 3):
  #   await ctx.send(**await self.mine_sweeper(size, bomb_count))

  async def mine_sweeper(self, size: int = 5, bomb_count: int = 3):
    """Source for this command: https://medium.com/swlh/this-is-how-to-create-a-simple-minesweeper-game-in-python-af02077a8de"""

    if size > 9:
      raise exceptions.ArgumentTooLarge("Size cannot be larger than 9 due to the message character limit of Discord")
    if bomb_count > size * size or bomb_count >= 81:
      raise exceptions.ArgumentTooLarge("Bomb count cannot be larger than the game board")
    if size <= 1 or bomb_count <= 1:
      raise exceptions.ArgumentTooSmall("Bomb count and board size must be greater than 1")

    arr = [[0 for row in range(size)] for column in range(size)]

    # async with ctx.channel.typing():
    async def get_xy() -> tuple:
      async with timeout(1):
        try:
          return await self.bot.loop.run_in_executor(None, random.randint, 0, size - 1), await self.bot.loop.run_in_executor(None, random.randint, 0, size - 1)
        except Exception as e:
          self.bot.logger.critical("This is what caused the shutdown")
          raise e

    for _ in range(bomb_count):
      x, y = await get_xy()
      while arr[y][x] == 'X':
        x, y = await get_xy()
      arr[y][x] = 'X'

      if (x >= 0 and x <= size - 2) and (y >= 0 and y <= size - 1):
        if arr[y][x + 1] != 'X':
          arr[y][x + 1] += 1  # center right

      if (x >= 1 and x <= size - 1) and (y >= 0 and y <= size - 1):
        if arr[y][x - 1] != 'X':
          arr[y][x - 1] += 1  # center left

      if (x >= 1 and x <= size - 1) and (y >= 1 and y <= size - 1):
        if arr[y - 1][x - 1] != 'X':
          arr[y - 1][x - 1] += 1  # top left

      if (x >= 0 and x <= size - 2) and (y >= 1 and y <= size - 1):
        if arr[y - 1][x + 1] != 'X':
          arr[y - 1][x + 1] += 1  # top right

      if (x >= 0 and x <= size - 1) and (y >= 1 and y <= size - 1):
        if arr[y - 1][x] != 'X':
          arr[y - 1][x] += 1  # top center

      if (x >= 0 and x <= size - 2) and (y >= 0 and y <= size - 2):
        if arr[y + 1][x + 1] != 'X':
          arr[y + 1][x + 1] += 1  # bottom right

      if (x >= 1 and x <= size - 1) and (y >= 0 and y <= size - 2):
        if arr[y + 1][x - 1] != 'X':
          arr[y + 1][x - 1] += 1  # bottom left

      if (x >= 0 and x <= size - 1) and (y >= 0 and y <= size - 2):
        if arr[y + 1][x] != 'X':
          arr[y + 1][x] += 1  # bottom center

    return dict(
        embed=embed(
            title=f"{size}x{size} with {bomb_count} bombs",
            author_name="Minesweeper",
            description="||" + "||\n||".join("||||".join(self.MINEEMOTES[cell] for cell in row) for row in arr) + "||"),
    )

  @commands.command(name='souptime', help='Soup Time')
  @commands.cooldown(1, 7, commands.BucketType.user)
  async def norm_souptime(self, ctx):
    await ctx.reply(**self.souptime())

  # @commands.cooldown(1,7, commands.BucketType.user)
  # @cog_ext.cog_slash(name='souptime', description="Soup!")
  # @checks.slash(user=False, private=True)
  # async def slash_souptime(self, ctx):
  #   await ctx.send(**self.souptime())

  def souptime(self):
    return dict(embed=embed(
        title="Here is sum soup, just for you",
        color=MessageColors.SOUPTIME,
        description="I hope you enjoy!",
        image=random.choice(config['soups'])
    ))

  @commands.command(name="coinflip", aliases=["coin"], help="Flip a coin")
  async def norm_coinflip(self, ctx):
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

  @commands.command(name="poll", extras={"examples": ["\"this is a title\" '1' '2' '3'"]}, help="Make a poll. Contain each option in qoutes `'option' 'option 2'`")
  # @commands.group(name="poll", extras={"examples": ["\"this is a title\" 1;;2;;3"]}, help="Make a poll. Seperate the options with `;;`")
  @commands.guild_only()
  @commands.bot_has_permissions(manage_messages=True)
  async def norm_poll(self, ctx: "MyContext", title: str, option1: str = None, option2: str = None, option3: str = None, option4: str = None, option5: str = None, option6: str = None, option7: str = None, option8: str = None, option9: str = None, option10: str = None):
    options = []
    for item in [option1, option2, option3, option4, option5, option6, option7, option8, option9, option10]:
      if item is not None:
        options.append(item)

    if len(options) < 2:
      return await ctx.reply(embed=embed(title="Please choose 2 or more options for this poll", color=MessageColors.ERROR))

    await self.poll(ctx, title, options)

  # @cog_ext.cog_slash(
  #     name="poll",
  #     description="Make a poll",
  #     options=[
  #         create_option("title", "The title of the poll", SlashCommandOptionType.STRING, True),
  #         create_option("option1", "Option for the poll", SlashCommandOptionType.STRING, True),
  #         create_option("option2", "Option for the poll", SlashCommandOptionType.STRING, True),
  #         create_option("option3", "Option for the poll", SlashCommandOptionType.STRING, False),
  #         create_option("option4", "Option for the poll", SlashCommandOptionType.STRING, False),
  #         create_option("option5", "Option for the poll", SlashCommandOptionType.STRING, False),
  #         create_option("option6", "Option for the poll", SlashCommandOptionType.STRING, False),
  #         create_option("option7", "Option for the poll", SlashCommandOptionType.STRING, False),
  #         create_option("option8", "Option for the poll", SlashCommandOptionType.STRING, False),
  #         create_option("option9", "Option for the poll", SlashCommandOptionType.STRING, False),
  #         create_option("option10", "Option for the poll", SlashCommandOptionType.STRING, False),
  #     ]
  # )
  # @checks.slash(user=True, private=False)
  # @commands.bot_has_permissions(manage_messages=True)
  # async def slash_poll(self, ctx, title, option1, option2, option3=None, option4=None, option5=None, option6=None, option7=None, option8=None, option9=None, option10=None):
  #   ...
  #   # options = []
  #   # for item in [option1, option2, option3, option4, option5, option6, option7, option8, option9, option10]:
  #   #   if item is not None:
  #   #     options.append(item)
  #   # await self.poll(ctx, title, options, True)

  def bar(self, iteration, total, length=25, decimals=1, fill="█"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '░' * (length - filledLength)
    return f"\r |{bar}| {percent}%"

  async def poll(self, ctx: "MyContext", title, options=None, slash=False):
    x = 0
    titles = []
    vals = []
    ins = []
    for opt in options:
      titles.append(f"{self.POLLEMOTES[x]}\t{opt}")
      vals.append(f"{self.bar(0,1)}")
      ins.append(False)
      x += 1
    message = await ctx.send(embed=embed(title=f"Poll: {title}", fieldstitle=titles, fieldsval=vals, fieldsin=ins))
    x = 0
    for _ in options:
      await message.add_reaction(self.POLLEMOTES[x])
      x += 1

  @commands.Cog.listener("on_raw_reaction_add")
  @commands.Cog.listener("on_raw_reaction_remove")
  async def on_raw_reaction(self, payload):
    if payload.member == self.bot.user:
      return
    if payload.emoji.name not in self.POLLEMOTES.values():
      return
    message = None
    try:
      message = await (self.bot.get_channel(payload.channel_id)).fetch_message(payload.message_id)
    except Exception:
      pass
    if message is None or message.author != self.bot.user:
      return
    if len(message.embeds) == 0:
      return
    if not message.embeds[0].title.startswith("Poll: ") and not message.embeds[0].title.startswith("Pole: "):
      return
    # for react in message.reactions:
    #   if not react.me and react.emoji not in self.POLLEMOTES.values():
    #     return

    available_reactions = []
    x = 0
    for _ in message.embeds[0].fields:
      available_reactions.append(self.POLLEMOTES[x])
      x += 1

    react_count = 0
    x = 0
    me = [me for me in (await message.reactions[x].users().flatten()) if me == self.bot.user] if len(message.reactions) == len(available_reactions) else []
    for item in available_reactions:
      if len(me) == 0:
        await message.add_reaction(item)
        message = await (self.bot.get_channel(payload.channel_id)).fetch_message(payload.message_id)
      react_count += message.reactions[x].count
      x += 1
    react_count = react_count - len(message.embeds[0].fields)
    react_count = react_count if react_count > 0 else 1

    x = 0
    titles = []
    vals = []
    ins = []
    for field in message.embeds[0].fields:
      titles.append(field.name)
      ins.append(False)
      vals.append(self.bar(message.reactions[x].count - 1, react_count))
      x += 1

    await message.edit(embed=embed(title=message.embeds[0].title.replace("Pole: ", "Poll: "), fieldstitle=titles, fieldsval=vals, fieldsin=ins))

  # @norm_poll.command(name="conclude", help="Concludes the poll", hidden=True)
  # @commands.guild_only()
  # @commands.bot_has_permissions(manage_messages=True)
  # async def norm_poll_conclude(self, ctx: "MyContext", poll: discord.Message):
  #   if not poll.embeds[0].title.startswith("Poll: "):
  #     return await ctx.send(embed=embed(title="That message is not a poll", color=MessageColors.ERROR))

  # @cog_ext.cog_subcommand(base="poll", base_desc="Make a poll", name="conclude", description="Concludes a poll", options=[create_option(name="message", description="The link to the poll message", option_type=SlashCommandOptionType.STRING, required=True)], guild_ids=[243159711237537802])
  # @checks.slash(user=True, private=False)
  # async def slash_poll_conclude(self, ctx: SlashContext, message: discord.Message):
  #   if not message.embeds[0].title.startswith("Poll: "):
  #     return await ctx.send(embed=embed(title="That message is not a poll", color=MessageColors.ERROR))


def setup(bot):
  bot.add_cog(Fun(bot))
