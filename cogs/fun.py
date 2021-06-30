import json
import random
import typing
import numpy as np
import asyncio
import datetime

import discord
from discord.ext import commands, tasks
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_choice, create_option, SlashCommandOptionType

# sys.path.insert(1, os.path.join(sys.path[0], '..'))
from pyfiglet import figlet_format
from functions import MessageColors, embed, exceptions, checks, query
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


with open('./config.json') as f:
  config = json.load(f)


class Fun(commands.Cog):
  """Fun things like games"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.rpsoptions = ["rock", "paper", "scissors"]
    self.countdowns = []
    self.countdown_messages = []
    self.loop_countdown.add_exception_type(discord.NotFound)
    self.loop_countdown.start()
    # self.timeouter = None
    # self.timeoutCh = None

  def cog_unload(self):
    self.loop_countdown.stop()

  @commands.Cog.listener()
  async def on_ready(self):

    self.countdowns = await query(self.bot.log.mydb, "SELECT * FROM countdowns")

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
  async def norm_rock_paper_scissors(self, ctx, args: str):
    async with ctx.typing():
      post = await self.rock_paper_scissors(ctx, args)
    await ctx.reply(**post)

  @cog_ext.cog_slash(
      name="rockpaperscissors",
      options=[
          create_option(
              "choice",
              description="Rock Paper or Scissors",
              option_type=3,
              required=True,
              choices=[
                  create_choice(
                      "rock",
                      "Rock"
                  ),
                  create_choice(
                      "paper",
                      "Paper"
                  ),
                  create_choice(
                      "scissors",
                      "Scissors"
                  )
              ]
          )
      ]
  )
  @checks.slash(user=False, private=True)
  async def slash_rock_paper_scissors(self, ctx, choice: str):
    await ctx.defer()
    post = await self.rock_paper_scissors(ctx, choice)
    await ctx.send(**post)

  async def rock_paper_scissors(self, ctx, args: str):
    # args = args.split(" ")
    # arg = args[0].lower()
    arg = args.lower()
    # if args not in self.options
    #   await ctx.reply(embed=embed(title="Please only choose one of three options, Rock, Paper, or Scissors",color=MessageColors.ERROR))
    #   return

    if arg not in self.rpsoptions:
      await ctx.reply(embed=embed(title=f"`{arg}` is not Rock, Paper, Scissors. Please choose one of those three.", color=MessageColors.ERROR))
      return

    num = random.randint(0, len(self.rpsoptions) - 1)

    mychoice = self.rpsoptions[num]

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

    return dict(
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
  async def norm_minesweeper(self, ctx, size: typing.Optional[int] = 5, bomb_count: typing.Optional[int] = 6):
    await ctx.reply(**await self.mine_sweeper(size, bomb_count))

  @cog_ext.cog_slash(
      name="minesweeper",
      description="Minesweeper",
      options=[
          create_option("size", "SizeXSize", SlashCommandOptionType.INTEGER, False),
          create_option("bomb_count", "Amount of bombs", SlashCommandOptionType.INTEGER, False)
      ]
  )
  @checks.slash(user=False, private=True)
  async def slash_minesweeper(self, ctx, size: int = 5, bomb_count: int = 3):
    await ctx.send(**await self.mine_sweeper(size, bomb_count))

  async def mine_sweeper(self, size, bomb_count):
    """Source for this command: https://medium.com/swlh/this-is-how-to-create-a-simple-minesweeper-game-in-python-af02077a8de"""

    if size > 9:
      raise exceptions.ArgumentTooLarge("Size cannot be larger than 9 due to the message character limit of Discord")
    if bomb_count > size * size:
      raise exceptions.ArgumentTooLarge("Bomb_count cannot be larger than the game board")

    arr = [[0 for row in range(size)] for column in range(size)]

    # async with ctx.channel.typing():
    def get_xy():
      return np.random.randint(0, size - 1), np.random.randint(0, size - 1)

    for _ in range(bomb_count):
      x, y = get_xy()
      while arr[y][x] == 'X':
        x, y = get_xy()
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
        delete_after=None)

  @commands.command(name='souptime', help='Soup Time')
  @commands.cooldown(1, 7, commands.BucketType.user)
  async def norm_souptime(self, ctx):
    await ctx.reply(**self.souptime())

  # @commands.cooldown(1,7, commands.BucketType.user)
  @cog_ext.cog_slash(name='souptime', description="Soup!")
  @checks.slash(user=False, private=True)
  async def slash_souptime(self, ctx):
    await ctx.send(**self.souptime())

  def souptime(self):
    return dict(embed=embed(
        title="Here is sum soup, just for you",
        color=MessageColors.SOUPTIME,
        description="I hope you enjoy!",
        image=random.choice(config['soups'])
    ))

  @commands.command(name="coinflip", aliases=["coin"], help="Flip a coin")
  async def norm_coin(self, ctx):
    await ctx.reply(embed=embed(title="The coin landed on: " + random.choice(["Heads", "Tails"])))

  @cog_ext.cog_slash(
      name="coinflip",
      description="Flip a coin"
  )
  @checks.slash(user=False, private=True)
  async def slash_coin(self, ctx):
    await ctx.send(embed=embed(title="The coin landed on: " + random.choice(["Heads", "Tails"])))

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

  @commands.command(name="poll", help="Make a poll. Seperate the options with `;;`")
  @commands.guild_only()
  @commands.bot_has_permissions(manage_messages=True)
  async def norm_poll(self, ctx, title, *, options: str = None):
    options = options.split(";;")

    if len(options) < 2:
      return await ctx.reply(embed=embed(title="Please choose 2 or more options for this poll", color=MessageColors.ERROR))

    await self.poll(ctx, title, options)

  @cog_ext.cog_slash(
      name="poll",
      description="Make a poll",
      options=[
          create_option("title", "The title of the poll", SlashCommandOptionType.STRING, True),
          create_option("option1", "Option for the poll", SlashCommandOptionType.STRING, True),
          create_option("option2", "Option for the poll", SlashCommandOptionType.STRING, True),
          create_option("option3", "Option for the poll", SlashCommandOptionType.STRING, False),
          create_option("option4", "Option for the poll", SlashCommandOptionType.STRING, False),
          create_option("option5", "Option for the poll", SlashCommandOptionType.STRING, False),
          create_option("option6", "Option for the poll", SlashCommandOptionType.STRING, False),
          create_option("option7", "Option for the poll", SlashCommandOptionType.STRING, False),
          create_option("option8", "Option for the poll", SlashCommandOptionType.STRING, False),
          create_option("option9", "Option for the poll", SlashCommandOptionType.STRING, False),
          create_option("option10", "Option for the poll", SlashCommandOptionType.STRING, False),
      ]
  )
  @checks.slash(user=True, private=False)
  @commands.bot_has_permissions(manage_messages=True)
  async def slash_poll(self, ctx, title, option1, option2, option3=None, option4=None, option5=None, option6=None, option7=None, option8=None, option9=None, option10=None):
    options = []
    for item in [option1, option2, option3, option4, option5, option6, option7, option8, option9, option10]:
      if item is not None:
        options.append(item)
    await self.poll(ctx, title, options, True)

  def bar(self, iteration, total, length=25, decimals=1, fill="█"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '░' * (length - filledLength)
    return f"\r |{bar}| {percent}%"

  async def poll(self, ctx, title, options=None, slash=False):
    x = 0
    titles = []
    vals = []
    ins = []
    for opt in options:
      titles.append(f"{self.POLLEMOTES[x]}\t{opt}")
      vals.append(f"{self.bar(0,1)}")
      ins.append(False)
      x += 1
    try:
      if slash:
        message = await ctx.send(embed=embed(title=f"Poll: {title}", fieldstitle=titles, fieldsval=vals, fieldsin=ins))
      else:
        message = await ctx.reply(embed=embed(title=f"Poll: {title}", fieldstitle=titles, fieldsval=vals, fieldsin=ins))
    except Exception as e:
      raise e
    else:
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

  @commands.command(name="gametime", help="Ping a role that is attached to a game and see who wants to play")
  @commands.guild_only()
  async def norm_game_time(self, ctx, role: discord.Role, *, message: str = None):
    await self.game_time(ctx, role, message)

  @cog_ext.cog_slash(
      name="gametime",
      description="Ping a role that's attached to a game and see who wants to play",
      options=[
          create_option("role", "Which role to mention", SlashCommandOptionType.ROLE, True),
          create_option("message", "Add a message to follow the mention", SlashCommandOptionType.STRING, False)
      ]
  )
  @checks.slash(user=True, private=False)
  async def slash_game_time(self, ctx, role, message=None):
    await self.game_time(ctx, role, message, True)

  async def game_time(self, ctx, role, message=None, slash=False):
    if role not in ctx.author.roles:
      if slash:
        return await ctx.send(hidden=True, content="Since this command is ment for game roles and you don't have that role, I will not go through with this command")
      return await ctx.reply(embed=embed(title="Since this command is ment for game roles and you don't have that role, I will not go through with this command", color=MessageColors.ERROR))

    mention_perm = ctx.author.permissions_in(ctx.channel).mention_everyone
    if not role.mentionable and not mention_perm:
      if slash:
        return await ctx.send(hidden=True, content="You don't have permission to mention that role")
      return await ctx.reply(embed=embed(title="You don't have permission to mention that role", color=MessageColors.ERROR))

    if slash:
      message = await ctx.send(content=f"{role.mention} {message if message is not None else ''}", allowed_mentions=discord.AllowedMentions(roles=True, everyone=False, users=False))
    else:
      await ctx.delete()
      message = await ctx.reply(content=f"{role.mention} {message if message is not None else ''}", allowed_mentions=discord.AllowedMentions(roles=True, everyone=False, users=False))

    await message.add_reaction("👍")
    await message.add_reaction("👎")

  def get_time(self, now: int, future: int):
    time = datetime.timedelta(seconds=future - now)
    sec = time.seconds
    hours = sec // 3600
    minutes = (sec // 60) - (hours * 60)
    sec = sec % 60
    return hours, minutes, sec

  @commands.command(name="countdown", aliases=["cd"], help="Start a countdown. This command only updates every 5 seconds to avoid being ratelimited by Discord")
  @commands.max_concurrency(3, commands.BucketType.guild, wait=True)
  async def countdown(self, ctx: commands.Context, hours: typing.Optional[int] = 0, minutes: typing.Optional[int] = 0, seconds: typing.Optional[int] = 0, title: str = None):
    if hours == 0 and minutes == 0 and seconds == 0:
      return await ctx.send_help(ctx.command)

    if hours < 0 or minutes < 0 or seconds < 0:
      return await ctx.reply(embed=embed(title="Only positive numbers are accepted", color=MessageColors.ERROR))

    current_countdowns = [item for item in self.countdowns if (item[0] is not None and item[0] == ctx.guild.id) or (item[0] is None and ctx.author.dm_channel is not None and item[1] == ctx.author.dm_channel.id)] if ctx.guild is not None else []
    if len(current_countdowns) > 5:
      if ctx.guild is not None:
        guild_min = await checks.guild_is_min_tier(self.bot, ctx.guild, "t1_one_guild")
        if len(current_countdowns) > 5 and not guild_min:
          return await ctx.reply(embed=embed(title="This server can only have a max of 5 concurrent countdowns per server", description="To unlock more please check out [patreon.com/fridaybot](https://www.patreon.com/bePatron?u=42649008)", color=MessageColors.ERROR))
        elif len(current_countdowns) > 20 and guild_min:
          return await ctx.reply(embed=embed(title="This server can only have a max of 20 concurrent countdowns per server", color=MessageColors.ERROR))
      if ctx.guild is None and ctx.author.dm_channel is not None:
        user_min = await checks.user_is_min_tier(self.bot, ctx.author, "t1_one_guild")
        if len(current_countdowns) > 5 and not user_min:
          return await ctx.reply(embed=embed(title="You can only have a max of 5 concurrent countdowns per server", description="To unlock more please check out [patreon.com/fridaybot](https://www.patreon.com/bePatron?u=42649008)", color=MessageColors.ERROR))
        elif len(current_countdowns) > 20 and user_min:
          return await ctx.reply(embed=embed(title="You can only have a max of 20 concurrent countdowns per server", color=MessageColors.ERROR))

    duration = datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)
    if duration.days > 0:
      return await ctx.reply(embed=embed(title="Countdowns can't be set to any longer than 24 hours", color=MessageColors.ERROR))
    now = datetime.datetime.utcnow().timestamp()
    future = now + duration.seconds
    hours, minutes, sec = self.get_time(now, future)
    message = await ctx.send(embed=embed(title=f"Countdown: {title if title is not None else ''}", description="```" + figlet_format(f"{hours}:{minutes}:{sec}") + "```"))
    await query(self.bot.log.mydb, "INSERT IGNORE INTO countdowns (guild,channel,message,title,time) VALUES (%s,%s,%s,%s,%s)", message.guild.id if message.guild is not None else None, message.channel.id, message.id, title, future)
    self.countdowns.append((message.guild.id if message.guild is not None else None, message.channel.id, message.id, title, future))
    self.countdown_messages.append((message, title, future))

  @tasks.loop(seconds=5.0)
  async def loop_countdown(self):
    while self.bot.is_closed():
      await asyncio.sleep(0.1)
    x, y, batch, batch_delete_db = 0, 0, [], []
    if len(self.countdown_messages) == 0:
      for guild_id, channel_id, message_id, title, time in self.countdowns:
        try:
          message = await (await self.bot.fetch_channel(channel_id)).fetch_message(message_id)
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
      batch.append(query(self.bot.log.mydb, f"DELETE FROM countdowns WHERE message IN ({', '.join(batch_delete_db)})"))
    await asyncio.gather(*batch)

  @commands.Cog.listener()
  async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
    while self.bot.is_closed():
      await asyncio.sleep(0.1)
    if payload.guild_id is not None and len([item for item in self.countdowns if item[2] == payload.message_id]) > 0:
      await query(self.bot.log.mydb, "DELETE FROM countdowns WHERE message=%s", payload.message_id)
      self.countdown_messages.pop(self.countdown_messages.index([i for i in self.countdown_messages if i[0].id == payload.message_id][0]))
      self.countdowns.pop(self.countdowns.index([i for i in self.countdowns if i[2] == payload.message_id][0]))

  @loop_countdown.before_loop
  async def before_loop_countdown(self):
    await self.bot.wait_until_ready()


def setup(bot):
  bot.add_cog(Fun(bot))
