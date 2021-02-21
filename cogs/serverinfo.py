from discord.ext import commands

from functions import embed,is_pm

class ServerInfo(commands.Cog):
  def __init__(self,bot):
    self.bot = bot

  @commands.command(name="serverinfo")
  @commands.guild_only()
  async def server_info(self,ctx):
    if is_pm(ctx) == True:
      return

    await ctx.reply(
      embed=embed(
        title=ctx.guild.name+" - Info",
        thumbnail=ctx.guild.icon_url,
        fieldstitle=["Server Name", "Members", "Server ID", "Region", "Verification level"],
        fieldsval=[ctx.guild.name, ctx.guild.member_count, ctx.guild.id, ctx.guild.region, ctx.guild.verification_level]
      ),mention_author=False
    )

def setup(bot):
  bot.add_cog(ServerInfo(bot))