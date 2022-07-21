import discord
# from typing import TYPE_CHECKING

# if TYPE_CHECKING:
#   from index import Friday as Bot


class PersistantButtons(discord.ui.View):
  def __init__(self):
    super().__init__(timeout=None)


class StopButton(PersistantButtons):
  @discord.ui.button(emoji="⏹", label="Stop", style=discord.ButtonStyle.danger, custom_id="stopbutton-stop")
  async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
    if interaction.message:
      await interaction.message.delete()


class Links(PersistantButtons):
  def __init__(self):
    super().__init__()
    for item in self.links:
      self.add_item(item)

  @discord.utils.cached_property
  def links(self) -> list:
    return [discord.ui.Button(label="Support Server", url="https://discord.gg/paMxRvvZFc", row=1),
            discord.ui.Button(label="Patreon", url="https://www.patreon.com/fridaybot", row=1),
            discord.ui.Button(label="Docs", url="https://docs.friday-bot.com/", row=1),
            discord.ui.Button(label="Vote", url="https://top.gg/bot/476303446547365891/vote", row=1)]
