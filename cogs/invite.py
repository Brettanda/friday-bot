from discord.utils import oauth_url, cached_property
from discord.ext import commands
from discord_slash import cog_ext
from functions import config, embed, MessageColors


class Invite(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @cached_property
  def link(self):
    return oauth_url(self.bot.user.id, permissions=config.invite_permissions, scopes=["bot", "applications.commands"])

  @commands.command("invite", description="Get the invite link to add me to your server")
  async def _norm_invite(self, ctx):
    await ctx.reply(embed=embed(title="Invite me :)", description=f"[Invite link]({self.link})"))

  @cog_ext.cog_slash(name="invite", description="Get the invite link to add me to your server")
  async def _slash_invite(self, ctx):
    await ctx.send(hidden=True, embed=embed(title="Invite me :)", description=f"[Invite link]({self.link})"))


def setup(bot):
  bot.add_cog(Invite(bot))
