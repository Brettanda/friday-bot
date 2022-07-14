# import discord
# from discord.ext import commands

# from functions import embed, MyContext, exceptions, MessageColors

# from typing import TYPE_CHECKING

# if TYPE_CHECKING:
#   from index import Friday as Bot


# class MissingReportChannel(exceptions.Base):
#   def __init__(self, message="There is not report channel setup for this server."):
#     super().__init__(message=message)


# class Report(commands.Cog):
#   def __init__(self, bot: "Bot"):
#     self.bot = bot

#   def __repr__(self) -> str:
#     return "<cogs.Report content=\"Pong\">"

#   def cog_check(self, ctx):
#     if ctx.guild is None:
#       raise commands.NoPrivateMessage("This command can only be used within a guild")
#     return True

#   async def cog_command_error(self, ctx: "MyContext", error: Exception):
#     error = getattr(error, "original", error)
#     just_send = (MissingReportChannel, commands.CommandNotFound)
#     if isinstance(error, just_send):
#       await ctx.send(embed=embed(str(error), color=MessageColors.error()))

#   @commands.group("report", invoke_without_command=True)
#   async def report(self, ctx: "MyContext", message: str):
#     channel_id = await ctx.db.fetchval("SELECT report_channel FROM servers WHERE id=$1 LIMIT 1", str(ctx.guild.id))
#     if channel_id is None:
#       raise MissingReportChannel()
#     channel = ctx.guild.get_channel(int(channel_id, base=10))
#     if channel is None:
#       channel = await ctx.guild.fetch_channel(int(channel_id, base=10))
#       if channel is None:
#         raise commands.ChannelNotFound("The report channel is not found. Please contact the server owner.")

#     await channel.send(embed=embed("Report", message, fieldstitle=["Author"], fieldsval=[ctx.author.mention], timestamp=ctx.message.created_at))
#     await ctx.send(embed=embed("Your report has been sent."))

#   @report.group("channel", invoke_without_command=True)
#   @commands.has_permissions(manage_guild=True)
#   async def report_channel(self, ctx: "MyContext", channel: discord.TextChannel):
#     await ctx.db.execute("UPDATE servers SET report_channel=$1 WHERE id=$2", str(channel.id), str(ctx.guild.id))
#     await ctx.send(embed=embed("Report channel set."))

#   @report_channel.command("clear")
#   @commands.has_permissions(manage_guild=True)
#   async def report_channel_clear(self, ctx: "MyContext"):
#     await ctx.db.execute("UPDATE servers SET report_channel=NULL WHERE id=$1", str(ctx.guild.id))
#     await ctx.send(embed=embed("Report channel cleared."))


async def setup(bot):
  ...
  # await bot.add_cog(Report(bot))
