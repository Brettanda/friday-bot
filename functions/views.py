import discord
# from typing_extensions import TYPE_CHECKING

# if TYPE_CHECKING:
#   from index import Friday as Bot


class PersistantButtons(discord.ui.View):
  def __init__(self):
    super().__init__(timeout=None)


class StopButton(PersistantButtons):
  @discord.ui.button(emoji="⏹", label="Stop", style=discord.ButtonStyle.danger, custom_id="stopbutton-stop")
  async def stop(self, button: discord.ui.Button, interaction: discord.Interaction):
    await interaction.message.delete()


class SupportIntroRoles(discord.ui.View):
  """This should only be used in the support guild"""

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(emoji="📌", label="Get Updates", style=discord.ButtonStyle.blurple, custom_id="support_updates")
  async def support_updates(self, button: discord.ui.Button, interaction: discord.Interaction):
    if interaction.guild_id != 707441352367013899 or interaction.channel_id != 707458929696702525 or interaction.message.id != 707520808448294983:
      return

    await interaction.response.defer(ephemeral=True)

    if interaction.user.pending:
      return await interaction.followup.send(ephemeral=True, content="You must complete the membership screening before you can receive this role")

    role = interaction.guild.get_role(848626624365592636)
    if role is None:
      return

    if not isinstance(interaction.user, discord.Member):
      return

    if role in interaction.user.roles:
      await interaction.user.remove_roles(role, reason="No more updates :(")
      await interaction.followup.send(ephemeral=True, content="You will no longer receive pings for updates")
    else:
      await interaction.user.add_roles(role, reason="Updates!")
      await interaction.followup.send(ephemeral=True, content="You will now be pinged when a new update comes out")


class Links(PersistantButtons):
  def __init__(self):
    super().__init__()
    for item in self.links:
      self.add_item(item)

  @discord.utils.cached_property
  def links(self) -> list:
    return [discord.ui.Button(label="Support", style=discord.ButtonStyle.link, url="https://discord.gg/paMxRvvZFc", row=1),
            discord.ui.Button(label="Patreon", style=discord.ButtonStyle.link, url="https://www.patreon.com/fridaybot", row=1),
            discord.ui.Button(label="Docs", style=discord.ButtonStyle.link, url="https://docs.friday-bot.com/", row=1),
            discord.ui.Button(label="Dashboard", style=discord.ButtonStyle.link, url="https://friday-bot.com/", row=1)]
