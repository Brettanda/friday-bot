from discord.ext import commands

from functions import embed,query,mydb_connect

class ServerInfo(commands.Cog):
  def __init__(self,bot):
    self.bot = bot

  @commands.command(name="serverinfo")
  @commands.guild_only()
  async def server_info(self,ctx):
    async with ctx.typing():
      mydb = mydb_connect()
      prefix,delete_after,musicchannel,defaultRole = query(mydb,f"SELECT prefix,autoDeleteMSGs,musicChannel,defaultRole FROM servers WHERE id=%s",ctx.guild.id)[0]
    await ctx.reply(
      embed=embed(
        title=ctx.guild.name+" - Info",
        thumbnail=ctx.guild.icon_url,
        fieldstitle=["Server Name", "Members", "Server ID", "Region", "Verification level","Command prefix","Delete Commands After","Music Channel","Default Role"],
        fieldsval=[ctx.guild.name, ctx.guild.member_count, ctx.guild.id, ctx.guild.region, ctx.guild.verification_level,prefix,f"{delete_after} seconds",ctx.guild.get_channel(musicchannel),ctx.guild.get_role(defaultRole)]
      )
    )

def setup(bot):
  bot.add_cog(ServerInfo(bot))