import random,discord,asyncio

# import functions.messagecolors as MessageColors

# class ChooseGame():
#   def __init__(self,bot,config):
#     self.bot = bot
#     self.config = config

async def choosegame(bot,config,interval,shard_id):
  while not bot.is_closed():
    num = random.randint(0,len(config['games']))
    gm = config['games'][num-1]

    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=gm),shard_id=shard_id)
    await asyncio.sleep(interval)