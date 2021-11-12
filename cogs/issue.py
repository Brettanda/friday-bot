import os

import nextcord as discord
from nextcord.ext import commands
from typing_extensions import TYPE_CHECKING

from functions import MessageColors, embed, relay_info  # ,checks

from .log import CustomWebhook

# from discord_slash import cog_ext


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

  @discord.utils.cached_property
  def log_issues(self) -> CustomWebhook:
    return CustomWebhook.partial(os.environ.get("WEBHOOKISSUESID"), os.environ.get("WEBHOOKISSUESTOKEN"), session=self.bot.session)

  @commands.command(name="issue", aliases=["problem", "feedback"], help="If you have an issue or noticed a bug with Friday, this will send a message to the developer.", usage="<Description of issue and steps to recreate the issue>")
  @commands.cooldown(1, 30, commands.BucketType.channel)
  @commands.has_guild_permissions(manage_guild=True)
  async def norm_issue(self, ctx, *, issue: str):
    confirm = await ctx.prompt("Please confirm your feedback.", embed=embed(title="Are you sure you would like to submit this issue?", description=f"{issue}"))
    if not confirm:
      return await ctx.send(embed=embed(title="Canceled", color=MessageColors.ERROR))
    await relay_info("", embed=embed(title="Issue", description=f"{issue}", author_icon=ctx.author.display_avatar.url, author_name=ctx.author.display_name), bot=self.bot, webhook=self.log_issues)


def setup(bot):
  bot.add_cog(Issue(bot))
