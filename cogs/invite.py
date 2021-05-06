from discord.ext import commands
from discord_slash import cog_ext
from functions import GlobalCog


class Invite(GlobalCog):
  def __init__(self, bot):
    super().__init__(bot)
    self.link = "https://discord.com/oauth2/authorize?client_id=476303446547365891&permissions=2469521478&scope=bot%20applications.commands"

  @commands.command("invite", description="Get the invite link to add me to your server")
  async def _norm_invite(self, ctx):
    await ctx.reply(content=self.link)

  @cog_ext.cog_slash(name="invite", description="Get the invite link to add me to your server")
  async def _slash_invite(self, ctx):
    await ctx.send(hidden=True, content=self.link)


def setup(bot):
  bot.add_cog(Invite(bot))
