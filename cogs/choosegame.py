from numpy import random

import discord
from discord.ext import tasks, commands

from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot

GAMES = [
    "Developing myself",
    "Minecraft 1.19",
    "Super Smash Bros. Ultimate",
    "Cyberpunk 2078",
    "Forza Horizon 6",
    "Red Dead Redemption 3",
    "Grand Theft Auto V",
    "Grand Theft Auto VI",
    "Grand Theft Auto IV",
    "Grand Theft Auto III",
    "Ori and the Will of the Wisps",
    "With the internet",
    "DOOM Eternal",
    "D&D (solo)",
    "Muck",
    "Big brain time",
    "Uploading your consciousness",
    "Learning everything on the Internet",
    "some games",
    "with Machine Learning",
    "Escape from Tarkov",
    # "Giving out inspirational quotes",
    {
        "type": discord.ActivityType.listening, "content": "myself"
    },
    {
        "type": discord.ActivityType.watching, "content": "", "stats": True
    }
]


class ChooseGame(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.choose_game.start()

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @tasks.loop(minutes=10.0)
  async def choose_game(self):
    for shard_id in self.bot.shards:
      if random.random() < 0.6:
        gm = random.choice(GAMES)

        if isinstance(gm, str):
          await self.bot.change_presence(
              activity=discord.Activity(
                  type=discord.ActivityType.playing,
                  name=gm
              ),
              shard_id=shard_id,
          )
        elif gm.get("stats", None) is True:
          if self.bot.canary or self.bot.prod:
            self.status_updates.start(shard_id)
        else:
          await self.bot.change_presence(
              activity=discord.Activity(
                  type=gm.get("type", discord.ActivityType.playing),
                  name=gm["content"]
              ),
              shard_id=shard_id
          )
      else:
        await self.bot.change_presence(activity=None, shard_id=shard_id)

    self.choose_game.change_interval(minutes=float(random.randint(5, 45)))
    if self.status_updates.is_running():
      self.status_updates.cancel()

  @commands.Cog.listener()
  async def on_ready(self):
    if self.choose_game.is_running():
      self.choose_game.restart()
    if self.status_updates.is_running():
      self.status_updates.cancel()

  @choose_game.before_loop
  async def before_choose_game(self):
    await self.bot.wait_until_ready()

  @tasks.loop(minutes=1)
  async def status_updates(self, shard_id: int):
    member_count = sum(guild.member_count for guild in self.bot.guilds)
    await self.bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.bot.guilds)} servers with {member_count} members"
        ),
        shard_id=shard_id
    )

  @status_updates.before_loop
  @choose_game.before_loop
  async def before_status_updates(self):
    await self.bot.wait_until_ready()

  def cog_unload(self):
    self.choose_game.cancel()
    self.status_updates.cancel()


def setup(bot):
  bot.add_cog(ChooseGame(bot))
