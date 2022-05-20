from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands
from numpy import random

from functions import MessageColors, embed, time

if TYPE_CHECKING:
  from discord.channel import VoiceChannel

  from cogs.reminder import Reminder, Timer
  from index import Friday


class NaCl(commands.Cog):
  def __init__(self, bot: Friday):
    self.bot: Friday = bot

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def sexed(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
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
      self.bot.logger.info(f"Failed the sexed check for {member} ({member.id})")
      return
    self.bot.logger.info(f"Sexed {member} ({member.id})")

    sex: Optional[VoiceChannel] = member.guild.get_channel(932111746620084224)  # type: ignore
    if sex is None:
      return

    if len(sex.voice_states) >= sex.user_limit:
      return

    await member.edit(voice_channel=sex, reason=f"Got that 6.9% Sexed: {member}")

  async def ghost_fapper(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
    # THE CROC
    if member.guild.id != 582046945674002442:
      return

    if member.bot:
      return

    if after.channel is None:
      return

    if not after.self_deaf:
      return

    reminder: Optional[Reminder] = self.bot.get_cog("Reminder")  # type: ignore
    if reminder is None:
      return

    two_min = time.FutureTime("2m")
    await reminder.create_timer(two_min.dt, "ghostfapper", member.guild.id, after.channel.id, member.id)

  @commands.Cog.listener()
  async def on_ghostfapper_timer_complete(self, timer: Timer) -> None:
    guild_id, vc_id, member_id = timer.args

    guild = self.bot.get_guild(guild_id)
    if guild is None:
      return

    member = await self.bot.get_or_fetch_member(guild, member_id)

    if member is None or member.voice is None:
      return

    if member.voice.channel is None:
      return

    if not member.voice.self_deaf:
      return

    try:
      await member.edit(voice_channel=None, reason="Ghost Fapper")
      await member.send(embed=embed(title="It's creepy when you leave a ghost in a voice channel.", color=MessageColors.error()))
    except Exception:
      pass

  async def cam_only(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
    # THE CROC
    if member.guild.id != 582046945674002442:
      return

    if after.channel is None:
      return

    if after.channel.id != 582046945674002450:
      return

    if member.bot:
      return

    if after.self_stream or after.self_video:
      return

    reminder: Optional[Reminder] = self.bot.get_cog("Reminder")  # type: ignore
    if reminder is None:
      return

    two_min = time.FutureTime("2m")
    await reminder.create_timer(two_min.dt, "camonly", member.guild.id, after.channel.id, member.id)

  @commands.Cog.listener()
  async def on_camonly_timer_complete(self, timer: Timer) -> None:
    guild_id, vc_id, member_id = timer.args

    guild = self.bot.get_guild(guild_id)
    if guild is None:
      return

    member = await self.bot.get_or_fetch_member(guild, member_id)

    if member is None or member.voice is None:
      return

    if member.voice.channel is None or member.voice.channel.id != vc_id:
      return

    if member.voice.self_stream or member.voice.self_video:
      return

    try:
      await member.edit(voice_channel=None, reason="Cam Only")
      await member.send(embed=embed(title="Your vibes seems kinda off 😦 <:grunch:785387930445152256>", color=MessageColors.error()))
    except Exception:
      pass

  @commands.Cog.listener()
  async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    await self.sexed(member, before, after)
    await self.ghost_fapper(member, before, after)
    await self.cam_only(member, before, after)


async def setup(bot):
  await bot.add_cog(NaCl(bot))
