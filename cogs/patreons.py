from discord.ext import commands
# from discord_slash import cog_ext

from functions import checks, MessageColors, embed, config, MyContext

# import discord
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class Patreons(commands.Cog):
  """Exlusive command for Friday's Patreon Patrons"""

  def __init__(self, bot: "Bot") -> None:
    self.bot = bot

  def __repr__(self) -> str:
    return "<cogs.Patreon>"

  @commands.group(name="patreon", description="Commands for Friday's Patrons", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  async def norm_patreon(self, ctx: "MyContext"):
    await ctx.send_help(ctx.command)

  @norm_patreon.group("server", description="Activate the server that you would like to apply your patronage to", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @checks.is_supporter()
  @checks.is_min_tier()
  async def norm_patreon_server(self, ctx: "MyContext"):
    await self.norm_patreon_server_true(ctx)

  @norm_patreon_server.command("true")
  @commands.guild_only()
  @checks.is_supporter()
  @checks.is_min_tier()
  async def norm_patreon_server_true(self, ctx: "MyContext"):
    guild_id, tier, patreon_user = (await self.bot.db.query("SELECT id,tier,patreon_user FROM servers WHERE id=$1", str(ctx.guild.id)))[0]
    if tier is None or patreon_user is None:
      user_tier = await self.bot.log.fetch_user_tier(ctx.author)
      # Probably check what server has it and remove it instead of saying the following
      if user_tier == config.PremiumTiers.tier_1 and len(await self.bot.db.query("SELECT tier,user_id FROM patrons WHERE user_id=$1", str(ctx.author.id))) >= 1:
        return await ctx.reply(embed=embed(title="You have already used your patronage on another server", color=MessageColors.ERROR))
      await self.bot.db.query("UPDATE servers SET tier=$1, patreon_user=$2 WHERE id=$3", str(user_tier), str(ctx.author.id), str(ctx.guild.id))
      # self.bot.log.change_guild_tier(ctx.guild.id, user_tier)
      await ctx.reply(embed=embed(title="New server activated"))
    elif patreon_user == ctx.author.id:
      await ctx.reply(embed=embed(title="You have already activated this server"))
    else:
      await ctx.reply(embed=embed(title="There is already a patreon member for this server", color=MessageColors.ERROR))

  @norm_patreon_server.command("false")
  @commands.guild_only()
  async def norm_patreon_server_false(self, ctx: "MyContext"):
    guild_id, tier, patreon_user = (await self.bot.db.query("SELECT id,tier,patreon_user FROM servers WHERE id=$1", str(ctx.guild.id)))[0]
    if patreon_user is None or tier is None:
      return await ctx.reply(embed=embed(title="This server is not activated", color=MessageColors.ERROR))
    if patreon_user != str(ctx.author.id):
      # Maybe check if the patreon user is still in the guild?
      return await ctx.reply(embed=embed(title="Only the original patreon user can use this command"))
    await self.bot.db.query("UPDATE servers SET tier=$1, patreon_user=$2 WHERE id=$3", None, None, str(ctx.guild.id))
    # self.bot.log.change_guild_tier(ctx.guild.id, None)
    await ctx.reply(embed=embed(title="Server deactivated 😢"))

  async def cog_command_error(self, ctx: "MyContext", error: commands.CommandError):
    if isinstance(error, commands.CheckFailure):
      return await ctx.send(embed=embed(title="You are not allowed to use this command", color=MessageColors.ERROR))


def setup(bot):
  bot.add_cog(Patreons(bot))
