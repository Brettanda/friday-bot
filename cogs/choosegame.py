import asyncio
from numpy import random

import discord
from discord.ext import tasks, commands
from functions import config

from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class ChooseGame(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.choose_game.start()

  @tasks.loop(minutes=10.0)
  async def choose_game(self):
    # This might run per shard
    for shard_id in self.bot.shards:
      if random.random() < 0.6:
        gm = random.choice(config.games)

        if isinstance(gm, str):
          await self.bot.change_presence(
              activity=discord.Activity(
                  type=discord.ActivityType.playing,
                  name=gm
              ),
              shard_id=shard_id,
          )
        elif gm.get("stats", None) is True:
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
    await asyncio.sleep(float(random.randint(5, 45)) * 60)
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

  @tasks.loop(seconds=5)
  async def status_updates(self, shard_id: int):
    await self.bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{len(self.bot.guilds)} servers"
        ),
        shard_id=shard_id
    )

  def cog_unload(self):
    self.choose_game.cancel()
    self.status_updates.cancel()


def setup(bot):
  bot.add_cog(ChooseGame(bot))
