from discord.ext import commands
from discord_slash import cog_ext

from functions import embed


class Info(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.group(name="info", description="Displays some information about myself :)")
  async def norm_info(self, ctx):
    await ctx.reply(**await self.info(ctx))

  @cog_ext.cog_slash(name="info", description="Displays some information about myself :)")
  async def slash_info(self, ctx):
    await ctx.defer()
    await ctx.send(**await self.info(ctx))

  async def info(self, ctx):
    activity = ctx.guild.me.activity.name if ctx.guild is not None and ctx.guild.me.activity is not None else self.bot.activity.name if self.bot.activity is not None else None
    return dict(
        embed=embed(
            title=f"{self.bot.user.name} - Info",
            thumbnail=self.bot.user.avatar_url,
            description="Some information about me, Friday ;)",
            fieldstitle=["Username", "Guilds joined", "Status", "Latency", "Shards", "Loving Life", "Existed since"],
            fieldsval=[self.bot.user.name, len(self.bot.guilds), activity, f"{self.bot.latency*1000:,.0f} ms", self.bot.shard_count, "True", self.bot.user.created_at]
            # fieldstitle=["Username","Guilds joined","Status","Latency","Shards","Audio Nodes","Loving Life","Existed since"],
            # fieldsval=[self.bot.user.name,len(self.bot.guilds),ctx.guild.me.activity.name if ctx.guild.me.activity is not None else None,f"{self.bot.latency*1000:,.0f} ms",self.bot.shard_count,len(self.bot.wavelink.nodes),"True",self.bot.user.created_at]
        )
    )


def setup(bot):
  bot.add_cog(Info(bot))
