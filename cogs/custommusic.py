import json

import validators
from discord.ext import commands

from cogs.music import can_play
from functions import MessageColors, embed, exceptions, query
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


# TODO: make slash commands for this cog
class CustomMusic(commands.Cog, name="Custom Music"):
  """Asign music urls to a command so you dont have to find the url everytime you want to play `bruh 2`"""

  def __init__(self, bot: "Bot"):
    self.bot = bot

  def cog_check(self, ctx):
    if ctx.guild is None:
      raise commands.NoPrivateMessage("This command can only be used within a guild")
    return True

  @commands.group(name="custom", aliases=["c"], invoke_without_command=True, description="Play sounds/songs without looking for the url everytime")
  # @commands.cooldown(1,4, commands.BucketType.channel)
  @commands.check(can_play)
  @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
  async def custom(self, ctx, name: str):
    try:
      async with ctx.typing():
        sounds = await query(self.bot.mydb, "SELECT customSounds FROM servers WHERE id=%s", ctx.guild.id)
        sounds = json.loads(sounds)
    except Exception:
      await ctx.reply(embed=embed(title=f"The custom sound `{name}` has not been set, please add it with `{ctx.prefix}custom|c add <name> <url>`", color=MessageColors.ERROR))
    else:
      if sounds is not None and name in sounds:
        await ctx.invoke(self.bot.get_command("play"), query=sounds[name])
      else:
        await ctx.reply(embed=embed(title=f"The sound `{name}` has not been added, please check the `custom list` command", color=MessageColors.ERROR))

  @custom.command(name="add")
  @commands.has_guild_permissions(manage_channels=True)
  async def custom_add(self, ctx, name: str, url: str):
    url = url.strip("<>")
    valid = validators.url(url)
    if valid is not True:
      await ctx.reply(embed=embed(title=f"Failed to recognize the url `{url}`", color=MessageColors.ERROR))
      return

    if name in ["add", "change", "replace", "list", "remove", "del"]:
      await ctx.reply(embed=embed(title=f"`{name}`is not an acceptable name for a command as it is a sub-command of custom", color=MessageColors.ERROR))
      return

    async with ctx.typing():
      name = "".join(name.split(" ")).lower()
      sounds = (await query(self.bot.mydb, "SELECT customSounds FROM servers WHERE id=%s", ctx.guild.id))
      if sounds == "" or sounds is None:
        sounds = r"{}"
      sounds = json.loads(sounds)
      if name in sounds:
        await ctx.reply(embed=embed(title=f"`{name}` was already added, please choose another", color=MessageColors.ERROR))
        return
      sounds.update({name: url})
      await query(self.bot.mydb, "UPDATE servers SET customSounds=%s WHERE id=%s", json.dumps(sounds), ctx.guild.id)
    await ctx.reply(embed=embed(title=f"I will now play `{url}` for the command `{ctx.prefix}{ctx.command.parent} {name}`"))

  @custom.command(name="list")
  async def custom_list(self, ctx):
    async with ctx.typing():
      sounds = await query(self.bot.mydb, "SELECT customSounds FROM servers WHERE id=%s", ctx.guild.id)
      if sounds is None:
        raise exceptions.NoCustomSoundsFound("There are no custom sounds for this server (yet)")
      sounds = json.loads(sounds)
      result = ""
      for sound in sounds:
        result += f"```{sound} -> {sounds[sound]}```"
      if result == "":
        result = "There are no custom sounds for this server (yet)"
    await ctx.reply(embed=embed(title="The list of custom sounds", description=result))

  @custom.command(name="change", aliases=["replace"])
  @commands.has_guild_permissions(manage_channels=True)
  async def custom_change(self, ctx, name: str, url: str):
    try:
      async with ctx.typing():
        name = "".join(name.split(" ")).lower()
        sounds = await query(self.bot.mydb, "SELECT customSounds FROM servers WHERE id=%s", ctx.guild.id)
        sounds = json.loads(sounds)
        old = sounds[name]
        sounds[name] = url
        await query(self.bot.mydb, "UPDATE servers SET customSounds=%s WHERE id=%s", json.dumps(sounds), ctx.guild.id)
    except KeyError:
      await ctx.reply(embed=embed(title=f"Could not find the custom command `{name}`", color=MessageColors.ERROR))
    else:
      await ctx.reply(embed=embed(title=f"Changed `{name}` from `{old}` to `{url}`"))

  @custom.command(name="remove", aliases=["del"])
  @commands.has_guild_permissions(manage_channels=True)
  async def custom_del(self, ctx, name: str):
    try:
      async with ctx.typing():
        name = "".join(name.split(" ")).lower()
        sounds = await query(self.bot.mydb, "SELECT customSounds FROM servers WHERE id=%s", ctx.guild.id)
        sounds = json.loads(sounds)
        del sounds[name]
        await query(self.bot.mydb, "UPDATE servers SET customSounds=%s WHERE id=%s", json.dumps(sounds), ctx.guild.id)
    except KeyError:
      await ctx.reply(embed=embed(title=f"Could not find the custom command `{name}`", color=MessageColors.ERROR))
    else:
      await ctx.reply(embed=embed(title=f"Removed the custom sound `{name}`"))


def setup(bot):
  bot.add_cog(CustomMusic(bot))
