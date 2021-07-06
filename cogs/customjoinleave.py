# import asyncio
import json
import typing

from discord.ext import commands

from functions import embed, query

# from discord_slash import cog_ext,SlashContext


class CustomJoinLeave(commands.Cog):

  def cog_check(self, ctx):
    if ctx.guild is None:
      raise commands.NoPrivateMessage("This command can only be used within a guild")
    return True

  @commands.command(name="customjoin", aliases=["cjoin"], description="To remove your sound call this command with no arguments", hidden=True)
  @commands.is_owner()
  async def custom_join(self, ctx, url: typing.Optional[str] = None):
    async with ctx.typing():

      reactions = await query(self.bot.log.mydb, "SELECT customJoinLeave FROM servers WHERE id=?", ctx.guild.id)
      if reactions is None:
        reactions = r"{}"
      reactions = json.loads(reactions)
      try:
        reactions[str(ctx.author.id)]["join"] = url if url is not None else None
      except KeyError:
        reactions.update({str(ctx.author.id): {"join": None, "leave": None}})
        reactions[str(ctx.author.id)]["join"] = url if url is not None else None

      await query(self.bot.log.mydb, "UPDATE servers SET customJoinLeave=? WHERE id=?", json.dumps(reactions), ctx.guild.id)
    await ctx.reply(embed=embed(title=f"The new join sound for `{ctx.author}` is now `{url}`"))

  @commands.command(name="customleave", aliases=["cleave"], description="To remove your sound call this command with no arguments", hidden=True)
  @commands.is_owner()
  async def custom_leave(self, ctx, url: typing.Optional[str] = None):
    async with ctx.typing():

      reactions = await query(self.bot.log.mydb, "SELECT customJoinLeave FROM servers WHERE id=?", ctx.guild.id)
      if reactions is None:
        reactions = r"{}"
      reactions = json.loads(reactions)
      try:
        reactions[str(ctx.author.id)]["leave"] = url if url is not None else None
      except KeyError:
        reactions.update({str(ctx.author.id): {"join": None, "leave": None}})
        reactions[str(ctx.author.id)]["leave"] = url if url is not None else None

      await query(self.bot.log.mydb, "UPDATE servers SET customJoinLeave=? WHERE id=?", json.dumps(reactions), ctx.guild.id)
    await ctx.reply(embed=embed(title=f"The new leave sound for `{ctx.author}` is now `{url}`"))

  # @commands.Cog.listener()
  # async def on_voice_state_update(self,member,before,after):
  #   # print(before.channel)
  #   # print(after.channel)
  #   if before.channel is not None:
  #     return

  #   reactions = await query(self.bot.log.mydb,"SELECT customJoinLeave FROM servers WHERE id=?",member.guild.id)
  #   reactions = json.loads(reactions)
  #   if str(member.id) in reactions:
  #     print(reactions[str(member.id)]["join"])
  #     # await self.bot.get_command("play").__call__(url=reactions[str(member.id)]["join"])
  #     await after.channel.connect(reconnect=False)
  #     await asyncio.sleep(5)
  #     await member.guild.voice_client.disconnect()


def setup(bot):
  bot.add_cog(CustomJoinLeave(bot))
