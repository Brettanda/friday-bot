import json
import os
import random

import discord
from discord.ext import commands, tasks

with open(
    os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "..", "config.json")
) as f:
  config = json.load(f)


class ChooseGame(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.loop = bot.loop
    self.choose_game.start()

  @tasks.loop(minutes=30.0)
  async def choose_game(self):
    for shard_id in self.bot.shards:
      gm = random.choice(config["games"])

      if random.random() < 0.6:
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.playing,
                name=gm
            ),
            shard_id=shard_id,
        )
      else:
        await self.bot.change_presence(activity=None, shard_id=shard_id)

  @choose_game.before_loop
  async def before_choose_game(self):
    await self.bot.wait_until_ready()

  def cog_unload(self):
    self.choose_game.cancel()


def setup(bot):
  bot.add_cog(ChooseGame(bot))
