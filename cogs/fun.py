import json
import random
import typing

from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_choice, create_option

# sys.path.insert(1, os.path.join(sys.path[0], '..'))
from functions import MessageColors, embed

with open('./config.json') as f:
  config = json.load(f)

class Fun(commands.Cog):
  def __init__(self,bot):
    self.bot = bot
    self.rpsoptions = ["rock","paper","scissors"]
    # self.timeouter = None
    # self.timeoutCh = None

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

  @commands.command(name="rockpaperscissors",description="Play Rock Paper Scissors with Friday",aliases=["rps"],usage="<rock, paper or scissors>")
  async def norm_rock_paper_scissors(self,ctx,args:str):
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
  async def slash_rock_paper_scissors(self,ctx,choice:str):
    await ctx.defer()
    post = await self.rock_paper_scissors(ctx, choice)
    await ctx.send(**post)

  async def rock_paper_scissors(self,ctx,args:str):
    # args = args.split(" ")
    # arg = args[0].lower()
    arg = args.lower()
    # if args not in self.options
    #   await ctx.reply(embed=embed(title="Please only choose one of three options, Rock, Paper, or Scissors",color=MessageColors.ERROR))
    #   return

    if arg not in self.rpsoptions:
      await ctx.reply(embed=embed(title=f"`{arg}` is not Rock, Paper, Scissors. Please choose one of those three.",color=MessageColors.ERROR))
      return

    num = random.randint(0,len(self.rpsoptions)-1)

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

    return dict(embed=embed(title=f"Your move: {arg} VS My move: {mychoice}",color=MessageColors.RPS,description=f"The winner of this round is: **{conclusion}**"))


  EMOTES = {
    "X":"💥",
    0:"0️⃣",
    1:"1️⃣",
    2:"2️⃣",
    3:"3️⃣",
    4:"4️⃣",
    5:"5️⃣",
    6:"6️⃣",
    7:"7️⃣",
    8:"8️⃣"
  }

  @commands.command(name="minesweeper",aliases=["ms"])
  async def norm_minesweeper(self,ctx,size:typing.Optional[int]=5,bomb_count:typing.Optional[int]=6):
    await ctx.reply(**await self.mine_sweeper(size,bomb_count))

  @cog_ext.cog_slash(
    name="minesweeper",
    description="Minesweeper",
    options=[
      create_option("size", "SizeXSize", 4, required=False),
      create_option("bomb_count", "Amount of bombs", 4, required=False),
      create_option("hidden", "To hide the command, or not to hide the command", 5, required=False)
    ],guild_ids=[243159711237537802,805579185879121940]
  )
  async def slash_minesweeper(self,ctx,size:int=5,bomb_count:int=6,hidden:bool=False):
    await ctx.defer(hidden)
    post = await self.mine_sweeper(size,bomb_count,hidden)
    if hidden:
      await ctx.send(hidden=True,**post)
    else:
      await ctx.send(**post)

  async def mine_sweeper(self,size,bomb_count,hidden=False):
    """Source for this command: https://medium.com/swlh/this-is-how-to-create-a-simple-minesweeper-game-in-python-af02077a8de"""
    if size > 9:
      return dict(content="Size cannot be larger than 9 due to the message character limit of Discord")
      # raise exceptions.ArgumentTooLarge("Size cannot be larger than 9 due to the message character limit of Discord")
    if bomb_count > size*size:
      return dict(content="Bomb_count cannot be larger than the game board")
      # raise exceptions.ArgumentTooLarge("Bomb_count cannot be larger than the game board")

    arr = [[0 for row in range(size)] for column in range(size)]

    # async with ctx.channel.typing():
    def get_xy():
      return random.randint(0,size-1),random.randint(0,size-1)

    for _ in range(bomb_count):
      x,y = get_xy()
      while arr[y][x] == 'X':
        x,y = get_xy()
      arr[y][x] = 'X'

      if (x >=0 and x <= size-2) and (y >= 0 and y <= size-1):
        if arr[y][x+1] != 'X':
          arr[y][x+1] += 1 # center right

      if (x >=1 and x <= size-1) and (y >= 0 and y <= size-1):
        if arr[y][x-1] != 'X':
          arr[y][x-1] += 1 # center left

      if (x >= 1 and x <= size-1) and (y >= 1 and y <= size-1):
        if arr[y-1][x-1] != 'X':
          arr[y-1][x-1] += 1 # top left

      if (x >= 0 and x <= size-2) and (y >= 1 and y <= size-1):
        if arr[y-1][x+1] != 'X':
          arr[y-1][x+1] += 1 # top right

      if (x >= 0 and x <= size-1) and (y >= 1 and y <= size-1):
        if arr[y-1][x] != 'X':
          arr[y-1][x] += 1 # top center

      if (x >=0 and x <= size-2) and (y >= 0 and y <= size-2):
        if arr[y+1][x+1] != 'X':
          arr[y+1][x+1] += 1 # bottom right

      if (x >= 1 and x <= size-1) and (y >= 0 and y <= size-2):
        if arr[y+1][x-1] != 'X':
          arr[y+1][x-1] += 1 # bottom left

      if (x >= 0 and x <= size-1) and (y >= 0 and y <= size-2):
        if arr[y+1][x] != 'X':
          arr[y+1][x] += 1 # bottom center

    if hidden:
      return dict(content=f"{size}x{size} with {bomb_count} bombs\n"+"||"+"||\n||".join("||||".join(self.EMOTES[cell] for cell in row) for row in arr)+"||")
    else:
      return dict(embed=embed(title=f"{size}x{size} with {bomb_count} bombs",author_name="Minesweeper",description="||"+"||\n||".join("||||".join(self.EMOTES[cell] for cell in row) for row in arr)+"||"),delete_after=None)

  @commands.command(name='souptime',help='Soup Time')
  @commands.cooldown(1,7, commands.BucketType.user)
  async def norm_souptime(self,ctx):
    await ctx.reply(**self.souptime())

  @cog_ext.cog_slash(name='souptime')
  # @commands.cooldown(1,7, commands.BucketType.user)
  async def slash_souptime(self,ctx):
    await ctx.defer()
    await ctx.send(**self.souptime())

  def souptime(self):
    return dict(embed=embed(
      title="Here is sum soup, just for you",
      color=MessageColors.SOUPTIME,
      description="I hope you enjoy!",
      image=random.choice(config['soups'])
    ))

def setup(bot):
  bot.add_cog(Fun(bot))
