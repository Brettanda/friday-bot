from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands
from numpy import random
import traceback

from functions import MessageColors, embed, time

if TYPE_CHECKING:
  from discord.channel import VoiceChannel

  from cogs.reminder import Timer
  from index import Friday

log = logging.getLogger(__name__)


class ElectionModal(discord.ui.Modal, title="Election submission"):
  egan = discord.ui.TextInput(
      label="Egan",
      placeholder="Acceptable inputs include: \"x\" or \"1\", \"2\", and \"3\". One being highest priority",
      required=False,
      min_length=1,
      max_length=1
  )
  logan = discord.ui.TextInput(
      label="Logan",
      placeholder="Acceptable inputs include: \"x\" or \"1\", \"2\", and \"3\". One being highest priority",
      required=False,
      min_length=1,
      max_length=1
  )
  vexx = discord.ui.TextInput(
      label="Vexx",
      placeholder="Acceptable inputs include: \"x\" or \"1\", \"2\", and \"3\". One being highest priority",
      required=False,
      min_length=1,
      max_length=1
  )

  async def on_submit(self, interaction: discord.Interaction) -> None:
    assert interaction.guild is not None

    the_list_items = [self.egan, self.logan, self.vexx]
    the_list = [x.value for x in the_list_items]

    unique_list = []
    for x in the_list:
      if x != "":
        if x not in unique_list:
          unique_list.append(x)
        else:
          await interaction.response.send_message("Your inputs cannot be the same as your other inputs. i.e you cannot vote 1 for everyone", ephemeral=True)
          return

    if len(unique_list) == 0:
      await interaction.response.send_message("Bruh. You didn't vote for anyone???????????????", ephemeral=True)
      return

    if any(v.lower() not in ["x", "1", "2", "3"] for v in unique_list):
      await interaction.response.send_message("Submission failed, please make sure that your inputs match any of the following:\n`x`, `1`, `2`, `3`", ephemeral=True)
      return

    if any(v.lower() == "x" for v in unique_list) and any(v.lower() in ["1", "2", "3"] for v in unique_list):
      await interaction.response.send_message("Submitting `x` means you don't want to rank your votes, so you're only voting for one candidate.", ephemeral=True)
      return

    submission_channel = interaction.guild.get_channel(1017527144181661767) or (await interaction.guild.fetch_channel(1017527144181661767))
    assert isinstance(submission_channel, discord.TextChannel)
    await submission_channel.send(embed=embed(
        author_name=f"{interaction.user.display_name} (ID: {interaction.user.id})",
        author_icon=interaction.user.display_avatar.url,
        title="Vote submission",
        fieldstitle=[x.label for x in the_list_items],
        fieldsval=[x.value or "No input" for x in the_list_items],
        fieldsin=[False] * len(the_list_items),
    ))
    await interaction.response.send_message("Your vote has been submitted", ephemeral=True)

  async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
    e = embed(title='Oops! Something went wrong.', color=MessageColors.red())
    if interaction.response.is_done():
      await interaction.followup.send(embed=e, ephemeral=True)
    else:
      await interaction.response.send_message(embed=e, ephemeral=True)

    # Make sure we know what the error actually is
    traceback.print_tb(error.__traceback__)


class ElectionButton(discord.ui.View):
  """This should only be used in the support guild"""

  def __init__(self):
    super().__init__(timeout=None)

  @discord.ui.button(emoji="🤱", label="Vote", style=discord.ButtonStyle.red, custom_id="election_button")
  async def support_updates(self, interaction: discord.Interaction, button: discord.ui.Button):
    await interaction.response.send_modal(ElectionModal())


class NaCl(commands.Cog):
  def __init__(self, bot: Friday):
    self.bot: Friday = bot

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @commands.Cog.listener()
  async def on_ready(self):
    if not self.bot.views_loaded:
      self.bot.add_view(ElectionButton())

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
      log.info(f"Failed the sexed check for {member} ({member.id})")
      return
    log.info(f"Sexed {member} ({member.id})")

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

    reminder = self.bot.reminder
    if reminder is None:
      return

    two_min = time.FutureTime("5m")
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
      if not random.random() < 0.0001:
        await member.send(embed=embed(title="It's creepy when you leave a ghost in a voice channel.", color=MessageColors.error()))
      else:
        await member.send("https://www.youtube.com/watch?v=NR9iGWyztck")
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

    reminder = self.bot.reminder
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
