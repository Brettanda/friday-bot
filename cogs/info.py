import discord
import datetime
from discord.ext import commands
from discord_slash import cog_ext
from discord_slash.model import SlashCommandOptionType
from discord_slash.utils.manage_commands import create_option

from functions import embed, query, MessageColors, checks, config
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class Info(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot

  @commands.group(name="info", aliases=["about"], help="Displays some information about myself :)")
  async def norm_info(self, ctx):
    await ctx.reply(**await self.info(ctx))

  @cog_ext.cog_slash(name="info", description="Displays some information about myself :)")
  async def slash_info(self, ctx):
    await ctx.defer()
    await ctx.send(**await self.info(ctx))

  async def info(self, ctx):
    appinfo = await self.bot.application_info()
    owner = appinfo.team.members[0]
    delta = datetime.datetime.utcnow() - self.bot.uptime
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime = "{h}h {m}m {s}s".format(h=hours, m=minutes, s=seconds)
    return dict(
        embed=embed(
            title=f"{self.bot.user.name} - About",
            thumbnail=self.bot.user.avatar_url,
            author_icon=owner.avatar_url,
            author_name=owner,
            description="Big thanks to all Patrons!",
            fieldstitle=["Servers joined", "Latency", "Shards", "Loving Life", "Uptime", "Existed since"],
            fieldsval=[len(self.bot.guilds), f"{(self.bot.get_shard(ctx.guild.shard_id).latency if ctx.guild else self.bot.latency)*1000:,.0f} ms", self.bot.shard_count, "True", uptime, self.bot.user.created_at.strftime("%b %d, %Y")],
            footer="Made with 💖 with discord.py"
            # fieldstitle=["Username","Guilds joined","Status","Latency","Shards","Audio Nodes","Loving Life","Existed since"],
            # fieldsval=[self.bot.user.name,len(self.bot.guilds),ctx.guild.me.activity.name if ctx.guild.me.activity is not None else None,f"{self.bot.latency*1000:,.0f} ms",self.bot.shard_count,len(self.bot.wavelink.nodes),"True",self.bot.user.created_at]
        ), components=[config.useful_buttons()]
    )

  @commands.command(name="serverinfo", help="Shows information about the server")
  @commands.guild_only()
  async def norm_server_info(self, ctx):
    post = await self.server_info(ctx)
    await ctx.reply(**post)

  @cog_ext.cog_slash(name="serverinfo", description="Info about a server")
  @commands.guild_only()
  async def slash_server_info(self, ctx):
    post = await self.server_info(ctx)
    await ctx.send(**post)

  async def server_info(self, ctx):
    # async with ctx.typing() if ctx.typing is not None else ctx.defer():
    prefix, delete_after, musicchannel, defaultRole = (await query(self.bot.log.mydb, "SELECT prefix,autoDeleteMSGs,musicChannel,defaultRole FROM servers WHERE id=?", ctx.guild.id))[0]
    return dict(
        embed=embed(
            title=ctx.guild.name + " - Info",
            thumbnail=ctx.guild.icon_url,
            fieldstitle=["Server Name", "Members", "Server ID", "Region", "Created", "Verification level", "Command prefix", "Delete Commands After"],
            fieldsval=[ctx.guild.name, ctx.guild.member_count, ctx.guild.id, ctx.guild.region, ctx.guild.created_at.strftime("%b %d, %Y"), ctx.guild.verification_level, prefix, f"{delete_after} seconds"]
            # fieldstitle=["Server Name", "Members", "Server ID", "Region", "Verification level", "Command prefix", "Delete Commands After", "Music Channel", "Default Role"],
            # fieldsval=[ctx.guild.name, ctx.guild.member_count, ctx.guild.id, ctx.guild.region, ctx.guild.verification_level, prefix, f"{delete_after} seconds", ctx.guild.get_channel(musicchannel), ctx.guild.get_role(defaultRole)]
        )
    )

  @commands.command(name="userinfo", help="Some information on the mentioned user")
  @commands.guild_only()
  async def norm_user_info(self, ctx, user: discord.Member):
    await self.user_info(ctx, user)

  @cog_ext.cog_slash(name="userinfo", description="Some information on the mentioned user", options=[create_option(name="user", description="The user to get info for", option_type=SlashCommandOptionType.USER, required=True)])
  @checks.slash(user=True, private=False)
  async def slash_user_info(self, ctx, user: discord.Member):
    await self.user_info(ctx, user, True)

  async def user_info(self, ctx, member: discord.Member, slash=False):
    e = embed(
        title=f"{member.name} - Info",
        thumbnail=member.avatar_url,
        fieldstitle=["Name", "Nickname", "Mention", "Role count", "Joined", "Top Role", "Pending"],
        fieldsval=[member.name, member.nick, member.mention, len(member.roles), member.joined_at.strftime("%b %d, %Y"), member.top_role.mention, member.pending],
        color=member.color if member.color.value != 0 else MessageColors.DEFAULT
    )
    if slash:
      return await ctx.send(embed=e)
    return await ctx.reply(embed=e)


def setup(bot):
  bot.add_cog(Info(bot))
