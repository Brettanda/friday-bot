import discord
# from typing_extensions import TYPE_CHECKING

# if TYPE_CHECKING:
#   from index import Friday as Bot


class PersistantButtons(discord.ui.View):
  def __init__(self):
    super().__init__(timeout=None)


class StopButton(PersistantButtons):
  @discord.ui.button(emoji="⏹", label="Stop", style=discord.ButtonStyle.danger, custom_id="stopbutton-stop")
  async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
    await interaction.message.delete()


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
