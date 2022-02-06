import discord
from discord.ext import commands
from numpy import random

from functions import time, embed, MessageColors

from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class NaCl(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot

  def __repr__(self) -> str:
    return "<cogs.NaCl>"

  async def sexed(self, member: discord.Member, before, after):
    # NaCl
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

  async def ghost_fapper(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    # THE CROC
    if member.guild.id != 582046945674002442:
      return

    if member.bot:
      return

    if after.channel is None:
      return

    if not after.self_deaf:
      return

    reminder = self.bot.get_cog("Reminder")
    if reminder is None:
      return

    two_min = time.FutureTime("2m")
    await reminder.create_timer(two_min.dt, "ghostfapper", member.guild.id, member.voice.channel.id, member.id)

  @commands.Cog.listener()
  async def on_ghostfapper_timer_complete(self, timer):
    guild_id, vc_id, member_id = timer.args

    guild = self.bot.get_guild(guild_id)
    member = await self.bot.get_or_fetch_member(guild, member_id)

    if member.voice is None:
      return

    if member.voice.channel is None:
      return

    if not member.voice.self_deaf:
      return

    try:
      await member.edit(voice_channel=None, reason="Ghost Fapper")
      await member.send(embed=embed(title="It's creepy when you leave a ghost in a voice channel.", color=MessageColors.ERROR))
    except Exception:
      pass

  @commands.Cog.listener()
  async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    await self.sexed(member, before, after)
    await self.ghost_fapper(member, before, after)


def setup(bot):
  bot.add_cog(NaCl(bot))
