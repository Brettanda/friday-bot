import discord
from discord.ext import commands
from numpy import random

from functions import MyContext

from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class NaCl(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot

  def __repr__(self) -> str:
    return "<cogs.NaCl>"

  def cog_check(self, ctx: "MyContext"):
    if ctx.guild.id == 215346091321720832:
      return True
    return False

  @commands.Cog.listener()
  async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if member.guild.id != 215346091321720832:
      return

    if member.guild.afk_channel is None:
      return

    if after.channel != member.guild.afk_channel:
      return

    if before.channel == after.channel:
      return

    if not random.random() < 0.069:
      return

    sex = self.bot.get_channel(932111746620084224)
    if sex is None:
      return

    if len(sex.voice_states) >= sex.user_limit:
      return

    await member.edit(voice_channel=sex, reason="Got that 6.9% Sexed")


def setup(bot):
  bot.add_cog(NaCl(bot))
