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
    self.status_update_shards = []

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @tasks.loop(minutes=10.0)
  async def choose_game(self):
    self.status_update_shards.clear()
    if self.status_updates.is_running():
      self.status_updates.cancel()

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
          self.status_update_shards.append(shard_id)
          if not self.status_updates.is_running():
            self.status_updates.start()
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

  @tasks.loop(minutes=1)
  async def status_updates(self):
    member_count = sum(guild.member_count for guild in self.bot.guilds)
    for shard in self.status_update_shards:
      await self.bot.change_presence(
          activity=discord.Activity(
              type=discord.ActivityType.watching,
              name=f"{len(self.bot.guilds)} servers with {member_count} members"
          ),
          shard_id=shard
      )

  @status_updates.before_loop
  @choose_game.before_loop
  async def before_status_updates(self):
    await self.bot.wait_until_ready()

  async def cog_load(self):
    self.choose_game.start()
    if self.status_updates.is_running():
      self.status_updates.cancel()

  async def cog_unload(self):
    self.choose_game.cancel()
    self.status_updates.cancel()


async def setup(bot):
  await bot.add_cog(ChooseGame(bot))
