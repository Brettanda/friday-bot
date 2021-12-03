import discord
from discord.ext import commands

from typing_extensions import TYPE_CHECKING
from functions import embed, MessageColors

if TYPE_CHECKING:
  from index import Friday as Bot


class Starboard(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.starboards = {}
    self.emoji = "⭐"
    self.bot.loop.create_task(self.setup())

  async def setup(self):
    c = await self.bot.db.query("SELECT id,starboard_stars,starboard_channel FROM servers WHERE starboard_channel IS NOT NULL")
    for guild_id, star_count, channel_id in c:
      self.starboards.update({guild_id: {"channel_id": channel_id, "stars": int(star_count)}})

  @commands.Cog.listener()
  async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
    if payload.emoji.name != self.emoji:
      return
    if payload.guild_id not in self.starboards:
      return
    if self.starboards[payload.guild_id]["stars"] == 0:
      return
    channel = self.bot.get_channel(payload.channel_id)
    if not channel:
      return
    starboard_channel = self.bot.get_channel(self.starboards[payload.guild_id]["channel_id"])
    if not starboard_channel:
      return
    if channel == starboard_channel:
      return
    message: discord.Message = await channel.fetch_message(payload.message_id)
    if not message:
      return
    reaction_count = [r.count for r in message.reactions if r.emoji == self.emoji][0]
    if reaction_count < self.starboards[payload.guild_id]["stars"]:
      return
    await starboard_channel.send(content=channel.mention, embed=embed(
        color=MessageColors.SOUPTIME,
        author_icon=message.author.avatar.url,
        author_name=message.author.name,
        description=message.clean_content,
        fieldstitle=["Reply to" if message.reference is not None else None, "Orignal Message"],
        fieldsval=[f"[Jump!]({message.reference.jump_url})" if message.reference is not None else None, f"[Jump!]({message.jump_url})"],
        fieldsin=False,
    ))


def setup(bot):
  ...
  # bot.add_cog(Starboard(bot))
