import asyncio

from discord.ext import commands
from discord_slash import cog_ext

from cogs.cleanup import get_delete_time
from functions import embed, relay_info


class Issue(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.command(name="issue", aliases=["problem"], description="If you have an issue or noticed a bug with Friday, this will send a message to the developer.", usage="<Description of issue and steps to recreate the issue>")
  @commands.cooldown(1, 30, commands.BucketType.channel)
  async def issue(self, ctx, *, issue: str):
    timeout = 20
    confirm = await ctx.reply(f"Please confirm your issue by reacting with ✅. This will cancel after {timeout} seconds", embed=embed(title="Are you sure you would like to submit this issue?", description=f"{issue}"))
    delay = await get_delete_time(ctx)
    await ctx.message.delete(delay=delay)
    await confirm.add_reaction("✅")

    def check(reaction, user):
      return str(reaction.emoji) == "✅" and user == ctx.author

    try:
      await self.bot.wait_for("reaction_add", timeout=float(timeout), check=check)
    except asyncio.TimeoutError:
      await confirm.edit(content="", embed=embed(title="Canceled"))
    else:
      await confirm.edit(content="", embed=embed(title="Sent"))
      await relay_info("", embed=embed(title="Issue", description=f"{issue}", ctx=ctx), bot=self.bot, channel=713270516487553055)
    finally:
      await confirm.delete(delay=delay)
      try:
        await confirm.clear_reaction("✅")
      except BaseException:
        await confirm.remove_reaction("✅", self.bot.user)

  @commands.command(name="support", description="Get an invite link to my support server")
  async def norm_support(self, ctx):
    await ctx.reply("https://discord.gg/NTRuFjU")

  @cog_ext.cog_slash(name="support", description="Support server link")
  async def slash_support(self, ctx):
    await ctx.defer(True)
    await ctx.send("https://discord.gg/NTRuFjU", hidden=True)


def setup(bot):
  bot.add_cog(Issue(bot))
