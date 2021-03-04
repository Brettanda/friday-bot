import discord,logging,os,json
from discord.ext import commands
# from discord_slash import cog_ext,SlashContext

from functions import embed,MessageColors,relay_info,mydb_connect,query,choosegame

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.json')) as f:
  config = json.load(f)

class Log(commands.Cog):
  """description goes here"""

  def __init__(self,bot):
    self.bot = bot
    self.loop = bot.loop

  @commands.Cog.listener()
  async def on_shard_connect(self,shard_id):
    print(f"Shard #{shard_id} has connected")
    logging.info(f"Shard #{shard_id} has connected")

  @commands.Cog.listener()
  async def on_ready(self):
    await relay_info(f"Apart of {len(self.bot.guilds)} guilds",self.bot)

  @commands.Cog.listener()
  async def on_shard_ready(self,shard_id):
    await relay_info(f"Logged on as #{shard_id} {self.bot.user}! - {self.bot.get_shard(shard_id).latency*1000:,.0f} ms",self.bot)
    self.loop.create_task(choosegame(self.bot,config,1800,shard_id),name="Gaming")
    # TODO: Check for new servers, if so add them to database, and remove rows if removed from server
    mydb = mydb_connect()
    database_guilds = query(mydb,f"SELECT id FROM servers")
    if len(database_guilds) != len(self.bot.guilds):
      current_guilds = []
      for guild in self.bot.guilds:
        current_guilds.append(guild.id)
      x = 0
      for guild in database_guilds:
        database_guilds[x] = guild[0]
        x = x + 1
      difference = list(set(database_guilds).symmetric_difference(set(current_guilds)))
      if len(difference) > 0:
        # now = datetime.now()
        if len(database_guilds) < len(current_guilds):
          for guild_id in difference:
            guild = self.bot.get_guild(guild_id)
            if guild is not None:
              owner = guild.owner.id if hasattr(guild,"owner") and hasattr(guild.owner,"id") else 0
              query(mydb,f"INSERT INTO servers (id,owner,name) VALUES (%s,%s,%s)",guild.id,owner,guild.name)
              if guild.system_channel is not None:
                prefix = "!"
                await guild.system_channel.send(
                  f"Thank you for inviting me to your server. My name is Friday, and I like to party. I will respond to some chats directed towards me and commands. To get started with commands type `{prefix}help`.\nAn example of something I will respond to is `Hello Friday` or `{self.bot.user.name} hello`. At my current stage of development I am very chaotic, so if I do something I shouldn't have please use send a message Issues channel in Friday's Development server. If something goes terribly wrong and you want it to stop, talk to my creator https://discord.gg/NTRuFjU"
                )
            else:
              print(f"HELP guild could not be found {guild_id}")
              logging.warning(f"HELP guild could not be found {guild_id}")
        elif len(database_guilds) > len(current_guilds):
          for guild_id in difference:
            query(mydb,f"DELETE FROM servers WHERE id=%s",guild_id)
        else:
          print("Could not sync guilds")
          logging.warning("Could not sync guilds")
          return
        print("Synced guilds with database")
        logging.info("Synced guilds with database")
    else:
      for guild_id in database_guilds:
        guild = self.bot.get_guild(guild_id[0])
        query(mydb,f"UPDATE servers SET name=%s WHERE id=%s",guild.name,guild_id[0])

  @commands.Cog.listener()
  async def on_shard_disconnect(self,shard_id):
    await relay_info(f"Shard #{shard_id} has disconnected",self.bot)

  @commands.Cog.listener()
  async def on_shard_reconnect(self,shard_id):
    await relay_info(f"Shard #{shard_id} has reconnected",self.bot)

  @commands.Cog.listener()
  async def on_shard_resumed(self,shard_id):
    await relay_info(f"Shard #{shard_id} has resumed",self.bot)

  @commands.Cog.listener()
  async def on_guild_join(self,guild):
    await relay_info("",self.bot,short=f"I have joined a new guild, making the total {len(self.bot.guilds)}",embed=embed(title=f"I have joined a new guild, making the total {len(self.bot.guilds)}"),channel=713270475031183390)
    # now = datetime.now()
    # current_time = now.strftime()
    mydb = mydb_connect()
    owner = guild.owner.id if hasattr(guild,"owner") and hasattr(guild.owner,"id") else 0
    query(mydb,f"INSERT INTO servers (id,owner,name) VALUES (%s,%s,%s)",guild.id,owner,guild.name)
    if guild.system_channel is not None:
      prefix = "!"
      await guild.system_channel.send(
        f"Thank you for inviting me to your server. My name is Friday, and I like to party. I will respond to some chats directed towards me and commands. To get started with commands type `{prefix}help`.\nAn example of something I will respond to is `Hello Friday` or `{self.bot.user.name} hello`. At my current stage of development I am very chaotic, so if I do something I shouldn't have please use send a message Issues channel in Friday's Development server. If something goes terribly wrong and you want it to stop, talk to my creator https://discord.gg/NTRuFjU"
      )

  @commands.Cog.listener()
  async def on_guild_remove(self,guild):
    await relay_info("",self.bot,short=f"I have been removed from a guild, making the total {len(self.bot.guilds)}",embed=embed(title=f"I have been removed from a guild, making the total {len(self.bot.guilds)}"),channel=713270475031183390)
    mydb = mydb_connect()
    query(mydb,f"DELETE FROM servers WHERE id=%s",guild.id)

  @commands.Cog.listener()
  async def on_member_join(self,member):
    mydb = mydb_connect()
    role_id = query(mydb,f"SELECT defaultRole FROM servers WHERE id=%s",member.guild.id)
    if role_id == 0 or role_id is None or str(role_id).lower() == "null":
      return
    else:
      role = member.guild.get_role(role_id)
      if role is None:
        # await member.guild.owner.send(f"The default role that was chosen for me to add to members when they join yours server \"{member.guild.name}\" could not be found, please update the default role at https://friday-self.bot.com")
        query(mydb,f"UPDATE servers SET defaultRole=NULL WHERE id=%s",member.guild.id)
      else:
        await member.add_roles(role,reason="Default Role")

def setup(bot):
  bot.add_cog(Log(bot))