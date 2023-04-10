from __future__ import annotations

import os
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
import logging

from functions import embed, MessageColors

from .log import CustomWebhook

if TYPE_CHECKING:
  from functions.custom_contexts import MyContext
  from index import Friday

log = logging.getLogger(__name__)


class SupportServer(discord.ui.View):
  def __init__(self):
    super().__init__()
    self.add_item(discord.ui.Button(label="Support Server", style=discord.ButtonStyle.grey, url="https://discord.gg/NTRuFjU"))


class Modal(discord.ui.Modal, title="Give feedback on Friday"):
  subject = discord.ui.TextInput(
      label="Subject",
      required=False,
      max_length=150
  )
  description = discord.ui.TextInput(
      label="Description",
      placeholder="Avoid using non-descriptive words like \"it glitches\" or \"its broken\"",
      style=discord.TextStyle.paragraph,
      required=True,
      max_length=1000
  )
  reproduce = discord.ui.TextInput(
      label="Steps to reproduce",
      placeholder="Describe how to reproduce your issue\nThis can be the command you used, button you clicked, etc...",
      style=discord.TextStyle.paragraph,
      required=True,
      max_length=1000
  )
  expected = discord.ui.TextInput(
      label="Expected result",
      placeholder="What should have happened?",
      style=discord.TextStyle.paragraph,
      required=True,
      max_length=1000
  )
  actual = discord.ui.TextInput(
      label="Actual result",
      placeholder="What actually happened?",
      style=discord.TextStyle.paragraph,
      required=True,
      max_length=1000
  )

  def __init__(self, cog: Issue, *args, **kwargs):
    self.cog: Issue = cog
    super().__init__(*args, **kwargs)

  async def on_submit(self, interaction: discord.Interaction):
    if all(x == self.children[0].value for x in self.children):  # type: ignore
      log.info(f"{interaction.user} ({interaction.user.id}) tried to make a dump ticket")
      return await interaction.response.send_message(embed=embed(title="Your issue was not sent", description="Please only submit real tickets", colour=MessageColors.red()), ephemeral=True)
    items = [c.value for c in self.children]  # type: ignore
    hook = self.cog.log_issues
    await interaction.response.send_message(embed=embed(title="Your issue has been submitted", description="Please join the support server for followup on your issue."), view=SupportServer(), ephemeral=True)
    try:
      await hook.send(
          embed=embed(
              title="Issue",
              fieldstitle=["Title", "Description", "Steps to reproduce", "Expected result", "Actual result"],
              fieldsval=[f"```\n{i}\n```" for i in items],
              fieldsin=[False] * len(items),
              author_icon=interaction.user.display_avatar.url,
              author_name=interaction.user.name + f" (ID: {interaction.user.id})"),
          username=self.cog.bot.user.name,
          avatar_url=self.cog.bot.user.display_avatar.url)
    except Exception:
      pass


class Issue(commands.Cog):
  """Report your issues you have with Friday"""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @discord.utils.cached_property
  def log_issues(self) -> CustomWebhook:
    return CustomWebhook.partial(os.environ.get("WEBHOOKISSUESID"), os.environ.get("WEBHOOKISSUESTOKEN"), session=self.bot.session)  # type: ignore

  @commands.hybrid_command(name="issue", aliases=["problem"])
  @commands.cooldown(1, 60, commands.BucketType.guild)
  @commands.has_guild_permissions(manage_guild=True)
  async def issue(self, ctx: MyContext):
    """If you have an issue or noticed a bug with Friday, this will send a message to the developer."""

    await ctx.prompt_modal(Modal(self))


async def setup(bot):
  await bot.add_cog(Issue(bot))
