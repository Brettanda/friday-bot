import os

import discord
from discord.ext import commands
from typing import Optional, List
from typing_extensions import TYPE_CHECKING

from functions import embed, MyContext  # ,checks

from .log import CustomWebhook

# from discord_slash import cog_ext


if TYPE_CHECKING:
  from index import Friday as Bot


class SupportServer(discord.ui.View):
  def __init__(self):
    super().__init__()
    self.add_item(discord.ui.Button(label="Support Server", style=discord.ButtonStyle.grey, url="https://discord.gg/NTRuFjU"))


class Modal(discord.ui.Modal):
  def __init__(self, title: str, items: List[dict], bot, author):
    super().__init__(title)
    self.bot = bot
    self.author = author
    self.values: Optional[list] = None
    for item in items:
      self.add_item(discord.ui.InputText(**item))

  async def callback(self, interaction: discord.Interaction):
    items = [c.value for c in self.children]
    hook = self.bot.get_cog("Issue").log_issues
    await interaction.response.send_message(embed=embed(title="Your issue has been submitted", description="Please join the support server for followup on your issue."), view=SupportServer(), ephemeral=True)
    await interaction.message.delete()
    try:
      await hook.send(
          embed=embed(
              title="Issue",
              fieldstitle=["Title", "Description", "Steps to reproduce", "Expected result", "Actual result"],
              fieldsval=[f"```\n{i}\n```" for i in items],
              fieldsin=[False for _ in range(len(items))],
              author_icon=self.author.display_avatar.url,
              author_name=self.author.name + f" (ID: {self.author.id})"),
          username=self.bot.user.name,
          avatar_url=self.bot.user.display_avatar.url)
    except Exception:
      pass


class ModalView(discord.ui.View):
  def __init__(self, *, modal_button: Optional[str] = "Modal", modal_title: Optional[str] = "Modal", modal_items: List[dict] = [], author, bot):
    super().__init__(timeout=60.0)
    self._modal_button: Optional[str] = modal_button
    self._modal_title: Optional[str] = modal_title
    self._modal_items: List[dict] = modal_items
    self.author = author
    self.bot = bot

    self.button_modal.label = modal_button

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if interaction.user and interaction.user.id == self.author.id:
      return True
    else:
      await interaction.response.send_message('This confirmation dialog is not for you.', ephemeral=True)
      return False

  @discord.ui.button(emoji="\N{WRITING HAND}", label="Modal", custom_id="issue_modal", style=discord.ButtonStyle.primary)
  async def button_modal(self, button, interaction: discord.Interaction):
    await interaction.response.send_modal(Modal(
        title=self._modal_title,
        items=self._modal_items,
        author=self.author,
        bot=self.bot
    ))

  @discord.ui.button(emoji="\N{HEAVY MULTIPLICATION X}", label='Cancel', custom_id="issue_cancel", style=discord.ButtonStyle.red)
  async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
    await interaction.response.defer()
    await interaction.delete_original_message()
    self.stop()

  async def on_timeout(self) -> None:
    try:
      await self.message.delete()
    except discord.NotFound:
      pass


class Issue(commands.Cog):
  """Report your issues you have with Friday"""

  def __init__(self, bot: "Bot"):
    self.bot = bot

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @discord.utils.cached_property
  def log_issues(self) -> CustomWebhook:
    return CustomWebhook.partial(os.environ.get("WEBHOOKISSUESID"), os.environ.get("WEBHOOKISSUESTOKEN"), session=self.bot.session)

  @commands.command(name="issue", aliases=["problem"], help="If you have an issue or noticed a bug with Friday, this will send a message to the developer.")
  @commands.cooldown(1, 60, commands.BucketType.guild)
  @commands.has_guild_permissions(manage_guild=True)
  async def issue(self, ctx: "MyContext"):
    await ctx.send(
        embed=embed(title="Please fill in the form from the button below."),
        view=ModalView(
            modal_button="Form",
            modal_title="Issue Form",
            modal_items=[
                dict(label="Subject", style=discord.InputTextStyle.singleline, required=False, max_length=150),
                dict(label="Description", placeholder="Avoid using non-descriptive words like \"it glitches\" or \"its broken\"", style=discord.InputTextStyle.paragraph, required=True, max_length=1000),
                dict(label="Steps to reproduce", placeholder="Describe how to reproduce your issue\nThis can be the command you used, button you clicked, etc...", style=discord.InputTextStyle.paragraph, required=True, max_length=1000),
                dict(label="Expected result", placeholder="What should have happened?", style=discord.InputTextStyle.paragraph, required=True, max_length=1000),
                dict(label="Actual result", placeholder="What actually happened?", style=discord.InputTextStyle.paragraph, required=True, max_length=1000)
            ],
            author=ctx.author,
            bot=self.bot
        ))


def setup(bot):
  bot.add_cog(Issue(bot))
