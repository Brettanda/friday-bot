from __future__ import annotations

from typing import TYPE_CHECKING, Union

import discord
import psutil
from discord.ext import commands
from discord.utils import cached_property, oauth_url

from functions import MessageColors, config, embed, time, views

if TYPE_CHECKING:
  from functions.custom_contexts import GuildContext, MyContext
  from index import Friday

GENERAL_CHANNEL_NAMES = {"welcome", "general", "lounge", "chat", "talk", "main"}


INVITE_PERMISSIONS = discord.Permissions(
    administrator=True,
    manage_roles=True,
    manage_channels=True,
    manage_guild=True,
    kick_members=True,
    ban_members=True,
    send_messages=True,
    manage_threads=True,
    send_messages_in_threads=True,
    create_private_threads=True,
    manage_messages=True,
    embed_links=True,
    attach_files=True,
    read_message_history=True,
    add_reactions=True,
    connect=True,
    speak=True,
    move_members=True,
    use_voice_activation=True,
    view_audit_log=True,
    moderate_members=True,
)


class InviteButtons(discord.ui.View):
  def __init__(self, link: str):
    super().__init__(timeout=None)
    self.add_item(discord.ui.Button(emoji="\N{HEAVY PLUS SIGN}", label="Invite me!", style=discord.ButtonStyle.link, url=link, row=1))


class General(commands.Cog):
  def __init__(self, bot: Friday):
    self.bot: Friday = bot
    self.process = psutil.Process()

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  def welcome_message(self, *, prefix: str = config.defaultPrefix) -> dict:
    friday_emoji = discord.PartialEmoji(name="friday", id=833507598413201459)
    return dict(embed=embed(
        title=f"{friday_emoji} Thank you for inviting me to your server {friday_emoji}",
        description=f"I will respond to messages when I am mentioned. To get started with commands type `{prefix}help` or `@{self.bot.user.name} help`.\n",
        footer="Made with ❤️ and discord.py!",
        fieldstitle=["Prefix", "Setting a language", "Chat channels", "Bug reporting", "Notice for chat system", "Support"],
        fieldsval=[
            f"To change my prefix use the `{prefix}prefix` command.",
            f"If you want me to speak another language then use the `{prefix}serverlang <language>`/`{prefix}userlang <language>` command eg.`{prefix}serverlang spanish` or `{prefix}userlang es`",
            f"To setup a channel where I respond to every message instead of @mentioning me, use `{prefix}chatchannel #chat-channel`",
            f"Found a bug with Friday? Report it with the `{prefix}issue` command.",
            "Chat message from Friday are not generated by a human, they are generated by an AI, the only response from a human is the **BOLDED** sensitive content message",
            "**For Friday's chatbot system to be free by default, ratelimits are in place. To get higher ratelimit caps, vote on top.gg or checkout the Patreon page.**"
        ],
        fieldsin=[False, False, False, False, False, False]
    ), view=views.Links())

  @commands.Cog.listener()
  async def on_guild_join(self, guild: discord.Guild):
    await self.bot.wait_until_ready()
    priority_channels = []
    channels = []
    for channel in guild.text_channels:
      if channel == guild.system_channel or any(x in channel.name for x in GENERAL_CHANNEL_NAMES):
        priority_channels.append(channel)
      else:
        channels.append(channel)
    channels = priority_channels + channels
    try:
      channel = next(
          x
          for x in channels
          if isinstance(x, discord.TextChannel) and x.permissions_for(guild.me).send_messages
      )
    except StopIteration:
      return

    try:
      await channel.send(**self.welcome_message())
    except discord.Forbidden:
      pass

    # try:
    #   audit = await guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add, after=after).flatten()
    #   if len(audit) == 0 or len([i for i in audit if i.target.id == self.bot.user.id and i.created_at > after]) == 0:
    #     return

    #   action: discord.AuditLogEntry = audit[0]
    #   await self.bot.db.query("UPDATE ")

  @commands.command(name="intro", help="Replies with the intro message for the bot")
  async def intro(self, ctx: MyContext):
    await ctx.send(**self.welcome_message())

  @cached_property
  def link(self):
    return oauth_url(self.bot.user.id, permissions=INVITE_PERMISSIONS, scopes=["bot", "applications.commands"])

  @commands.hybrid_command("invite", help="Get the invite link to add me to your server")
  async def _invite(self, ctx: MyContext):
    await ctx.send(embed=embed(title="Invite me :)"), view=InviteButtons(self.link))

  @commands.command(name="info", aliases=["about"], help="Displays some information about myself :)")
  async def info(self, ctx: MyContext):
    uptime = time.human_timedelta(self.bot.uptime, accuracy=None, brief=True, suffix=False)

    memory_usage = self.process.memory_full_info().uss / 1024**2
    cpu_usage = self.process.cpu_percent() / psutil.cpu_count()

    shard: discord.ShardInfo = self.bot.get_shard(ctx.guild.shard_id)  # type: ignore  # will never be None

    return await ctx.send(
        embed=embed(
            title=f"{self.bot.user.name} - About",
            thumbnail=self.bot.user.display_avatar.url,
            author_icon=self.bot.owner.display_avatar.url,
            author_name=str(self.bot.owner),
            footer="Made with ❤️ and discord.py!",
            description="Big thanks to all Patrons!",
            fieldstitle=["Servers joined", "Latency", "Shards", "Loving Life", "Uptime", "CPU/RAM", "Existed since"],
            fieldsval=[len(self.bot.guilds), f"{(shard.latency if ctx.guild else self.bot.latency)*1000:,.0f} ms", self.bot.shard_count, "True", uptime, f'{memory_usage:.2f} MiB\n{cpu_usage:.2f}% CPU', f"<t:{int(self.bot.user.created_at.timestamp())}:D>"],
        ), view=views.Links()
    )

  @commands.command(name="serverinfo", aliases=["guildinfo"], help="Shows information about the server")
  @commands.guild_only()
  async def serverinfo(self, ctx: GuildContext):
    await ctx.send(
        embed=embed(
            title=ctx.guild.name + " - Info",
            thumbnail=getattr(ctx.guild.icon, "url"),
            fieldstitle=["Server Name", "Members", "Server ID", "Created", "Verification level", "Roles"],
            # fieldsval=[f"```py\n{ctx.guild.name}```", f"```py\n{ctx.guild.member_count}```", f"```py\n{ctx.guild.id}```", f"```py\n{ctx.guild.region}```", f'```py\n{ctx.guild.created_at.strftime("%b %d, %Y")}```', f"```py\n{ctx.guild.verification_level}```", f"```py\n{len(ctx.guild.roles)}```"]
            fieldsval=[ctx.guild.name, ctx.guild.member_count, ctx.guild.id, time.format_dt(ctx.guild.created_at, style="D"), ctx.guild.verification_level, len(ctx.guild.roles)],
            footer=f"Shard: {ctx.guild.shard_id+1}/{self.bot.shard_count}",
        )
    )

  @commands.command(name="userinfo", extras={"examples": ["@Friday", "476303446547365891"]}, help="Some information on the mentioned user")
  @commands.guild_only()
  async def userinfo(self, ctx: GuildContext, *, user: Union[discord.Member, discord.User] = None):
    user = user or ctx.author
    await ctx.send(embed=embed(
        title=f"{user.name} - Info",
        thumbnail=user.display_avatar.url,
        fieldstitle=["Name", "Nickname", "Mention", "Role count", "Created", "Joined", "Top Role", "Pending Verification"],
        fieldsval=[
            user.name,
            user.display_name if user.display_name != user.name else None,
            user.mention,
            len(getattr(user, "roles", [])),
            time.format_dt(user.created_at, style="D") if hasattr(user, "created_at") else None,
            isinstance(user, discord.Member) and user.joined_at and time.format_dt(user.joined_at, style="D"),
            getattr(getattr(user, "top_role"), "mention"),
            getattr(user, "pending", None)],
        color=user.color if user.color.value != 0 else MessageColors.default()
    ))

  @commands.command(name="roleinfo", help="Shows information about the role")
  @commands.guild_only()
  async def roleinfo(self, ctx: GuildContext, *, role: discord.Role):
    await ctx.send(embed=embed(
        title=f"{role.name} - Info",
        thumbnail=getattr(role.icon, "url", None),
        fieldstitle=["Role Name", "Role ID", "Role Color", "Role Position", "Role Hoisted", "Role Mentionable", "Role Created"],
        fieldsval=[role.name, role.id, role.color, role.position, role.hoist, role.mentionable, time.format_dt(role.created_at, style="D")],
        color=role.colour if role.colour.value != 0 else MessageColors.default()
    ))


async def setup(bot: Friday):
  await bot.add_cog(General(bot))
