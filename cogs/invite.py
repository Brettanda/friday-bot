from discord.utils import oauth_url, cached_property
from discord.ext import commands
from discord_slash import cog_ext
from functions import config, embed


class Invite(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.id = 476303446547365891

  @commands.Cog.listener()
  async def on_ready(self):
    self.id = self.bot.user.id

  @cached_property
  def link(self):
    return oauth_url(self.id, permissions=config.invite_permissions, scopes=["bot", "applications.commands"])

  @commands.command("invite", description="Get the invite link to add me to your server")
  async def _norm_invite(self, ctx):
    await ctx.reply(embed=embed(title="Invite me :)", description=f"[Invite link]({self.link})"))

  @cog_ext.cog_slash(name="invite", description="Get the invite link to add me to your server")
  async def _slash_invite(self, ctx):
    await ctx.send(embed=embed(title="Invite me :)", description=f"[Invite link]({self.link})"))


def setup(bot):
  bot.add_cog(Invite(bot))
