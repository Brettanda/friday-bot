import discord

from discord.ext import commands
from discord_slash import cog_ext

from functions import embed, relay_info, checks, MessageColors
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class Confirm(discord.ui.View):
  def __init__(self, bot: "Bot"):
    self.bot = bot
    super().__init__(timeout=None)

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    cached_original_message = interaction.message.reference.cached_message
    original_message = cached_original_message if cached_original_message is not None else await interaction.channel.fetch_message(interaction.message.reference.message_id)
    original_author = original_message.author
    if original_message and original_author.id == interaction.user.id:
      return True
    if interaction.user.id == interaction.message.author.id:
      return True
    return False

  @discord.ui.button(emoji="✅", label="Confirm", custom_id="issue_confirm", style=discord.ButtonStyle.green)
  async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
    await interaction.response.edit_message(content="", embed=embed(title="Sent. For a follow up to this issue please join the support server"), view=SupportServer())
    await relay_info("", embed=embed(title="Issue", description=f"{interaction.message.embeds[0].description}", author_icon=interaction.user.avatar.url, author_name=interaction.user.name), bot=self.bot, webhook=self.bot.log.log_issues)

  @discord.ui.button(emoji="❌", label="Cancel", custom_id="issue_cancel", style=discord.ButtonStyle.grey)
  async def cancel(self, button: discord.ui.Button, interaction: discord.Integration):
    await interaction.response.edit_message(content="", embed=embed(title="Canceled", color=MessageColors.ERROR), view=None)


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

  @commands.Cog.listener()
  async def on_ready(self):
    if not self.bot.views_loaded:
      self.bot.add_view(Confirm(self.bot))

  @commands.command(name="issue", aliases=["problem", "feedback"], help="If you have an issue or noticed a bug with Friday, this will send a message to the developer.", usage="<Description of issue and steps to recreate the issue>")
  @commands.cooldown(1, 30, commands.BucketType.channel)
  async def norm_issue(self, ctx, *, issue: str):
    await self.issue(ctx, issue)

  @cog_ext.cog_slash(name="issue", description="If you have an issue or noticed a bug with Friday, this will send a message to the developer.")
  @checks.slash(user=True, private=False)
  async def slash_issue(self, ctx, *, issue: str):
    await self.issue(ctx, issue, True)

  async def issue(self, ctx, issue: str, slash=False):
    await ctx.send("Please confirm your feedback.", embed=embed(title="Are you sure you would like to submit this issue?", description=f"{issue}"), view=Confirm(self.bot))


def setup(bot):
  bot.add_cog(Issue(bot))
