import validators,json
from discord.ext import commands

from cogs.music import can_play

class CustomMusic(commands.Cog):
  """Asign music urls to a command so you dont have to find the url everytime you want to play `bruh 2`"""

  def __init__(self,bot):
    self.bot = bot

  async def cog_check(self,ctx):
    if ctx.guild is None:
      raise commands.NoPrivateMessage("This command can only be used within a guild")
    return True

  @commands.group(name="custom",aliases=["c"],invoke_without_command=True,description="Play sounds/songs without looking for the url everytime")
  # @commands.cooldown(1,4, commands.BucketType.channel)
  @commands.check(can_play)
  @commands.max_concurrency(1,commands.BucketType.channel,wait=True)
  async def custom(self,ctx,name:str):
    try:
      async with ctx.typing():
        mydb = mydb_connect()
        sounds = query(mydb,f"SELECT customSounds FROM servers WHERE id=%s",ctx.guild.id)
        sounds = json.loads(sounds)
    except KeyError:
      await ctx.reply(embed=embed(title=f"Could not find the custom command `{name}`",color=MessageColors.ERROR))
    except:
      raise
    else:
      if name in sounds:
        await ctx.invoke(self.bot.get_command("play"),url=sounds[name])
      else:
        await ctx.reply(embed=embed(title=f"Failed to play the custom sound `{name}`",color=MessageColors.ERROR))

  @custom.command(name="add")
  @commands.has_guild_permissions(manage_channels=True)
  async def custom_add(self,ctx,name:str,url:str):
    valid = validators.url(url)
    if valid is not True:
      await ctx.reply(embed=embed(title=f"Failed to recognize the url `{url}`",color=MessageColors.ERROR))
      return

    if name in ["add","change","replace","list","remove","del"]:
      await ctx.reply(embed=embed(title=f"`{name}`is not an acceptable name for a command as it is a sub-command of custom",color=MessageColors.ERROR))
      return

    try:
      async with ctx.typing():
        name = "".join(name.split(" ")).lower()
        mydb = mydb_connect()
        tier,sounds = query(mydb,f"SELECT tier,customSounds FROM servers WHERE id=%s",ctx.guild.id)[0]
        if sounds == "":
          sounds = r"{}"
        sounds = json.loads(sounds)
        if name in sounds:
          await ctx.reply(embed=embed(title=f"`{name}` was already added, please choose another",color=MessageColors.ERROR))
          return
        sounds.update({name:url})
        query(mydb,f"UPDATE servers SET customSounds=%s WHERE id=%s",json.dumps(sounds),ctx.guild.id)
    except:
      raise
    else:
      await ctx.reply(embed=embed(title=f"I will now play `{url}` for the command `{ctx.prefix}{ctx.command.parent} {name}`"))
   

  @custom.command(name="list")
  async def custom_list(self,ctx):
    try:
      async with ctx.typing():
        mydb = mydb_connect()
        sounds = query(mydb,f"SELECT customSounds FROM servers WHERE id=%s",ctx.guild.id)
        sounds = json.loads(sounds)
        result = ""
        for sound in sounds:
          result += f"```{sound} -> {sounds[sound]}```\n"
        if result == "":
          result = "There are no custom sounds for this server (yet)"
    except:
      raise
    else:
      await ctx.reply(embed=embed(title=f"The list of custom sounds",description=result))

  @custom.command(name="change",aliases=["replace"])
  @commands.has_guild_permissions(manage_channels=True)
  async def custom_change(self,ctx,name:str,url:str):
    try:
      async with ctx.typing():
        name = "".join(name.split(" ")).lower()
        mydb = mydb_connect()
        sounds = query(mydb,f"SELECT customSounds FROM servers WHERE id=%s",ctx.guild.id)
        sounds = json.loads(sounds)
        old = sounds[name]
        sounds[name] = url
        query(mydb,f"UPDATE servers SET customSounds=%s WHERE id=%s",json.dumps(sounds),ctx.guild.id)
    except KeyError:
      await ctx.reply(embed=embed(title=f"Could not find the custom command `{name}`",color=MessageColors.ERROR))
    except:
      raise
    else:
      await ctx.reply(embed=embed(title=f"Changed `{name}` from `{old}` to `{url}`"))

  @custom.command(name="remove",aliases=["del"])
  @commands.has_guild_permissions(manage_channels=True)
  async def custom_del(self,ctx,name:str):
    try:
      async with ctx.typing():
        name = "".join(name.split(" ")).lower()
        mydb = mydb_connect()
        sounds = query(mydb,f"SELECT customSounds FROM servers WHERE id=%s",ctx.guild.id)
        sounds = json.loads(sounds)
        del sounds[name]
        query(mydb,f"UPDATE servers SET customSounds=%s WHERE id=%s",json.dumps(sounds),ctx.guild.id)
    except KeyError:
      await ctx.reply(embed=embed(title=f"Could not find the custom command `{name}`",color=MessageColors.ERROR))
    except:
      raise
    else:
      await ctx.reply(embed=embed(title=f"Removed the custom sound `{name}`"))

def setup(bot):
  bot.add_cog(CustomMusic(bot))