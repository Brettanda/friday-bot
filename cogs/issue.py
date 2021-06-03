import asyncio

from discord.ext import commands
from discord_slash import cog_ext

from functions import embed, relay_info, checks


class Issue(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.command(name="issue", aliases=["problem"], description="If you have an issue or noticed a bug with Friday, this will send a message to the developer.", usage="<Description of issue and steps to recreate the issue>")
  @commands.cooldown(1, 30, commands.BucketType.channel)
  async def norm_feedback(self, ctx, *, issue: str):
    await self.feedback(ctx, issue)

  @cog_ext.cog_slash(name="issue", description="If you have an issue or noticed a bug with Friday, this will send a message to the developer.")
  @commands.cooldown(1, 30, commands.BucketType.channel)
  @checks.slash(user=True, private=False)
  async def slash_feedback(self, ctx, *, issue: str):
    await self.feedback(ctx, issue, True)

  async def feedback(self, ctx, issue: str, slash=False):
    timeout = 20
    if slash:
      confirm = await ctx.send(f"Please confirm your feedback by reacting with ✅. This will cancel after {timeout} seconds", embed=embed(title="Are you sure you would like to submit this issue?", description=f"{issue}"))
    else:
      confirm = await ctx.reply(f"Please confirm your feedback by reacting with ✅. This will cancel after {timeout} seconds", embed=embed(title="Are you sure you would like to submit this issue?", description=f"{issue}"))
    delay = self.bot.log.get_guild_delete_commands(ctx.guild)
    if not slash:
      try:
        await ctx.message.delete(delay=delay)
      except Exception:
        pass
    await confirm.add_reaction("✅")

    def check(reaction, user):
      return str(reaction.emoji) == "✅" and user == ctx.author

    try:
      await self.bot.wait_for("reaction_add", timeout=float(timeout), check=check)
    except asyncio.TimeoutError:
      await confirm.edit(content="", embed=embed(title="Canceled"), mention_author=False)
    else:
      await confirm.edit(content="", embed=embed(title="Sent. For a follow up to this issue please join the support server https://discord.gg/NTRuFjU"), mention_author=False)
      await relay_info("", embed=embed(title="Issue", description=f"{issue}", ctx=ctx), bot=self.bot, webhook=self.bot.log_issues)
    finally:
      if not slash:
        await confirm.delete(delay=delay if delay is not None else 30)
      try:
        await confirm.clear_reaction("✅")
      except Exception:
        await confirm.remove_reaction("✅", self.bot.user)


def setup(bot):
  bot.add_cog(Issue(bot))
