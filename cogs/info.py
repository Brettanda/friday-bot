import nextcord as discord
import datetime
import typing
import psutil
from nextcord.ext import commands
# from discord_slash import cog_ext
# from discord_slash.model import SlashCommandOptionType
# from discord_slash.utils.manage_commands import create_option

from functions import embed, MessageColors, views, MyContext  # , checks
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class Info(commands.Cog):
  """Grab information about your Discord server members with Friday's information commands"""

  def __init__(self, bot: "Bot"):
    self.bot = bot

  def __repr__(self):
    return "<cogs.Info>"

  @commands.command(name="info", aliases=["about"], help="Displays some information about myself :)")
  async def norm_info(self, ctx):
    await self.info(ctx)

  async def info(self, ctx: "MyContext"):
    appinfo = await self.bot.application_info()
    owner = appinfo.team.members[0]
    delta = datetime.datetime.utcnow() - self.bot.uptime
    weeks, remainder = divmod(int(delta.total_seconds()), 604800)
    days, remainder = divmod(remainder, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if weeks > 0:
      uptime = "{w}w {d}d {h}h".format(w=weeks, d=days, h=hours)
    elif days > 0:
      uptime = "{d}d {h}h {m}m".format(d=days, h=hours, m=minutes)
    else:
      uptime = "{h}h {m}m {s}s".format(h=hours, m=minutes, s=seconds)
    return await ctx.send(
        embed=embed(
            title=f"{self.bot.user.name} - About",
            thumbnail=self.bot.user.display_avatar.url,
            author_icon=owner.display_avatar.url,
            author_name=owner,
            description="Big thanks to all Patrons!",
            fieldstitle=["Servers joined", "Latency", "Shards", "Loving Life", "Uptime", "CPU/RAM", "Existed since"],
            fieldsval=[len(self.bot.guilds), f"{(self.bot.get_shard(ctx.guild.shard_id).latency if ctx.guild else self.bot.latency)*1000:,.0f} ms", self.bot.shard_count, "True", uptime, f"CPU: {psutil.cpu_percent()}%\nRAM: {psutil.virtual_memory()[2]}%", f"<t:{int(self.bot.user.created_at.timestamp())}:D>"],
        ), view=views.Links()
    )

  @commands.command(name="serverinfo", aliases=["guildinfo"], help="Shows information about the server")
  @commands.guild_only()
  async def norm_serverinfo(self, ctx):
    await self.server_info(ctx)

  # @cog_ext.cog_slash(name="serverinfo", description="Info about a server")
  # @commands.guild_only()
  # async def slash_serverinfo(self, ctx):
  #   await self.server_info(ctx)

  async def server_info(self, ctx: "MyContext"):
    return await ctx.send(
        embed=embed(
            title=ctx.guild.name + " - Info",
            thumbnail=ctx.guild.icon.url if ctx.guild.icon is not None else None,
            fieldstitle=["Server Name", "Members", "Server ID", "Region", "Created", "Verification level", "Roles"],
            # fieldsval=[f"```py\n{ctx.guild.name}```", f"```py\n{ctx.guild.member_count}```", f"```py\n{ctx.guild.id}```", f"```py\n{ctx.guild.region}```", f'```py\n{ctx.guild.created_at.strftime("%b %d, %Y")}```', f"```py\n{ctx.guild.verification_level}```", f"```py\n{len(ctx.guild.roles)}```"]
            fieldsval=[ctx.guild.name, ctx.guild.member_count, ctx.guild.id, ctx.guild.region, ctx.guild.created_at.strftime("%b %d, %Y"), ctx.guild.verification_level, len(ctx.guild.roles)]
        )
    )

  @commands.command(name="userinfo", extras={"examples": ["@Friday", "476303446547365891"]}, help="Some information on the mentioned user")
  @commands.guild_only()
  async def norm_userinfo(self, ctx, user: typing.Optional[discord.Member] = None):
    await self.user_info(ctx, user if user is not None else ctx.author)

  # @cog_ext.cog_slash(name="userinfo", description="Some information on the mentioned user", options=[create_option(name="user", description="The user to get info for", option_type=SlashCommandOptionType.USER, required=False)])
  # @checks.slash(user=True, private=False)
  # async def slash_userinfo(self, ctx, user: typing.Optional[discord.Member] = None):
  #   await self.user_info(ctx, user if user is not None else ctx.author)

  async def user_info(self, ctx: "MyContext", member: discord.Member):
    return await ctx.send(embed=embed(
        title=f"{member.name} - Info",
        thumbnail=member.display_avatar.url,
        fieldstitle=["Name", "Nickname", "Mention", "Role count", "Created", "Joined", "Top Role", "Pending Verification"],
        fieldsval=[member.name, str(member.nick), member.mention, len(member.roles), member.created_at.strftime("%b %d, %Y"), member.joined_at.strftime("%b %d, %Y"), member.top_role.mention, member.pending],
        color=member.color if member.color.value != 0 else MessageColors.DEFAULT
    ))


def setup(bot):
  bot.add_cog(Info(bot))
