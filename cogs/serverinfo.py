from discord.ext import commands

from functions import embed

class ServerInfo(commands.Cog):
  def __init__(self,bot):
    self.bot = bot

  @commands.command(name="serverinfo")
  @commands.guild_only()
  @commands.bot_has_permissions(send_messages = True, read_messages = True, manage_messages = True)
  async def server_info(self,ctx):
    await ctx.reply(
      embed=embed(
        title=ctx.guild.name+" - Info",
        thumbnail=ctx.guild.icon_url,
        fieldstitle=["Server Name", "Members", "Server ID", "Region", "Verification level"],
        fieldsval=[ctx.guild.name, ctx.guild.member_count, ctx.guild.id, ctx.guild.region, ctx.guild.verification_level]
      )
    )

def setup(bot):
  bot.add_cog(ServerInfo(bot))