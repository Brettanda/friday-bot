import nextcord as discord

from nextcord.ext import commands
# from discord_slash import cog_ext

from functions import embed, relay_info, MessageColors  # ,checks
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class SupportServer(discord.ui.View):
  def __init__(self):
    super().__init__()
    self.add_item(discord.ui.Button(label="Support Server", style=discord.ButtonStyle.grey, url="https://discord.gg/NTRuFjU"))


class Issue(commands.Cog):
  """Report your issues you have with Friday"""

  def __init__(self, bot: "Bot"):
    self.bot = bot

  def __repr__(self):
    return "<cogs.Issue>"

  @commands.command(name="issue", aliases=["problem", "feedback"], help="If you have an issue or noticed a bug with Friday, this will send a message to the developer.", usage="<Description of issue and steps to recreate the issue>")
  @commands.cooldown(1, 30, commands.BucketType.channel)
  async def norm_issue(self, ctx, *, issue: str):
    await self.issue(ctx, issue)

  # @cog_ext.cog_slash(name="issue", description="If you have an issue or noticed a bug with Friday, this will send a message to the developer.")
  # @checks.slash(user=True, private=False)
  # async def slash_issue(self, ctx, *, issue: str):
  #   await self.issue(ctx, issue, True)

  async def issue(self, ctx, issue: str, slash=False):
    confirm = await ctx.prompt("Please confirm your feedback.", embed=embed(title="Are you sure you would like to submit this issue?", description=f"{issue}"))
    if not confirm:
      return await ctx.send(embed=embed(title="Canceled", color=MessageColors.ERROR))
    await relay_info("", embed=embed(title="Issue", description=f"{issue}", author_icon=ctx.user.avatar.url, author_name=ctx.user.name), bot=self.bot, webhook=self.bot.log.log_issues)


def setup(bot):
  bot.add_cog(Issue(bot))
