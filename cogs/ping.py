from discord.ext import commands
from discord_slash import cog_ext

from functions import embed

# import discord

from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class Ping(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot

  @commands.command(name="ping", description="Pong!")
  async def norm_ping(self, ctx):
    # view = discord.ui.View()
    # message = await ctx.channel.send(**await self.ping(ctx))
    await self.ping(ctx)
    # view.add_item(discord.ui.Button(style=discord.ButtonStyle.primary, label="click me!", custom_id=f"{ctx.channel.id}-{message.id}"))
    # await message.edit(view=view)

  @cog_ext.cog_slash(name="ping", description="Ping!")
  async def slash_ping(self, ctx):
    await self.ping(ctx, True)

  # @commands.Cog.listener()
  # async def on_interaction(self, interation):
  #   if interation.user.bot:
  #     return

  #   print(interation)
  #   return

  async def ping(self, ctx, slash: bool = False):
    # buttons = discord.Button({"type": 2, "style": discord.ButtonStyle.primary, "disabled": False, "label": "Click Me!"})
    # buttons = discord.Button(type=2,style=discord.ButtonStyle.primary, label="Click me")
    # buttons = discord.Button({"type": 2, "style": discord.ButtonStyle.primary, "label": "FUCK"})
    # buttons = discord.Component({"type": 1, "components": [{"type": 2, "label": "Click Me!", "style": 1, "custom_id": "click_one"}]})
    # discord.ui.View()
    latency = f"{self.bot.get_shard(ctx.guild.shard_id).latency*1000:,.0f}" if ctx.guild is not None else f"{self.bot.latency*1000:,.0f}"
    if slash:
      return await ctx.send(embed=embed(title="Pong!", description=f"⏳ Latency is {latency}ms"))
    message = await ctx.send(embed=embed(title="Pong!")) if slash else await ctx.reply(embed=embed(title="Pong!"))
    ms = int((message.created_at - ctx.message.created_at).total_seconds() * 1000)
    await message.edit(embed=embed(title="Pong!", description=f"⏳ Latency is {ms}ms\n⌛ Average is {latency}ms"))


def setup(bot):
  bot.add_cog(Ping(bot))
