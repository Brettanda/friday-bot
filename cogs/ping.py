from discord.ext import commands
from discord_slash import cog_ext

from functions import embed

# import discord


class Ping(commands.Cog):
  @commands.command(name="ping", description="Pong!")
  async def norm_ping(self, ctx):
    # view = discord.ui.View()
    # message = await ctx.channel.send(**await self.ping(ctx))
    await ctx.reply(**await self.ping(ctx))
    # view.add_item(discord.ui.Button(style=discord.ButtonStyle.primary, label="click me!", custom_id=f"{ctx.channel.id}-{message.id}"))
    # await message.edit(view=view)

  @cog_ext.cog_slash(name="ping", description="Ping!")
  async def slash_ping(self, ctx):
    await ctx.send(**await self.ping(ctx))

  # @commands.Cog.listener()
  # async def on_interaction(self, interation):
  #   if interation.user.bot:
  #     return

  #   print(interation)
  #   return

  async def ping(self, ctx):
    # buttons = discord.Button({"type": 2, "style": discord.ButtonStyle.primary, "disabled": False, "label": "Click Me!"})
    # buttons = discord.Button(type=2,style=discord.ButtonStyle.primary, label="Click me")
    # buttons = discord.Button({"type": 2, "style": discord.ButtonStyle.primary, "label": "FUCK"})
    # buttons = discord.Component({"type": 1, "components": [{"type": 2, "label": "Click Me!", "style": 1, "custom_id": "click_one"}]})
    # discord.ui.View()

    return dict(embed=embed(title="Pong!"))


def setup(bot):
  bot.add_cog(Ping(bot))
