import nextcord as discord
from nextcord.utils import oauth_url, cached_property
from nextcord.ext import commands
# from discord_slash import cog_ext
from functions import embed
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot

INVITE_PERMISSIONS = discord.Permissions(
    administrator=True,
    manage_roles=True,
    manage_channels=True,
    manage_guild=True,
    kick_members=True,
    ban_members=True,
    send_messages=True,
    manage_threads=True,
    send_messages_in_threads=True,
    create_private_threads=True,
    manage_messages=True,
    embed_links=True,
    attach_files=True,
    read_message_history=True,
    add_reactions=True,
    connect=True,
    speak=True,
    move_members=True,
    use_voice_activation=True
)


class InviteButtons(discord.ui.View):
  def __init__(self, link: str):
    super().__init__(timeout=None)
    self.add_item(discord.ui.Button(emoji="\N{HEAVY PLUS SIGN}", label="Invite me!", style=discord.ButtonStyle.link, url=link, row=1))


class Invite(commands.Cog):
  """Invite Friday to your server"""

  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.id = 476303446547365891 if self.bot.prod else 760615464300445726 if self.bot.canary else 751680714948214855

  def __repr__(self):
    return "<cogs.Invite>"

  @cached_property
  def link(self):
    return oauth_url(self.id, permissions=INVITE_PERMISSIONS, scopes=["bot", "applications.commands"])

  @commands.command("invite", help="Get the invite link to add me to your server")
  async def _norm_invite(self, ctx):
    await ctx.send(embed=embed(title="Invite me :)"), view=InviteButtons(self.link))

  # @cog_ext.cog_slash(name="invite", description="Get the invite link to add me to your server")
  # async def _slash_invite(self, ctx):
  #   await ctx.send(embed=embed(title="Invite me :)", description=f"[Invite link]({self.link})"))


def setup(bot):
  bot.add_cog(Invite(bot))
