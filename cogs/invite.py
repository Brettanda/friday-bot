from nextcord.utils import oauth_url, cached_property
from nextcord.ext import commands
# from discord_slash import cog_ext
from functions import config, embed
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class Invite(commands.Cog):
  """Invite Friday to your server"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.id = 476303446547365891 if self.bot.prod else 760615464300445726 if self.bot.canary else 751680714948214855

  def __repr__(self):
    return "<cogs.Invite>"

  @cached_property
  def link(self):
    return oauth_url(self.id, permissions=config.invite_permissions, scopes=["bot", "applications.commands"])

  @commands.command("invite", help="Get the invite link to add me to your server")
  async def _norm_invite(self, ctx):
    await ctx.reply(embed=embed(title="Invite me :)", description=f"[Invite link]({self.link})"))

  # @cog_ext.cog_slash(name="invite", description="Get the invite link to add me to your server")
  # async def _slash_invite(self, ctx):
  #   await ctx.send(embed=embed(title="Invite me :)", description=f"[Invite link]({self.link})"))


def setup(bot):
  bot.add_cog(Invite(bot))
