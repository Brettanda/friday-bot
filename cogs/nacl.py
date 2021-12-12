from discord.ext import commands
from mcrcon import MCRcon
import os
from functions import embed, MyContext, MessageColors

from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


# https://pypi.org/project/mcrcon/


class NaCl(commands.Cog, command_attrs=dict(hidden=True)):
  def __init__(self, bot: "Bot"):
    self.bot = bot

    bot.loop.create_task(self.setup())

  def __repr__(self) -> str:
    return "<cogs.NaCl>"

  async def setup(self):
    try:
      self.mcron = await self.bot.loop.run_in_executor(None, MCRcon, os.environ["NACL_IP"], os.environ["NACL_PASS"], port=os.environ["NACL_PORT"])
      self.mcron.connect()
    except KeyError:
      self.mcron = None

  def cog_unload(self):
    if self.mcron:
      self.mcron.disconnect()

  async def cog_check(self, ctx: "MyContext") -> bool:
    if ctx.author.id not in (222560984709988352, 215227961048170496):
      raise commands.NotOwner()
    return True

  @commands.group("nacl", invoke_without_command=True)
  async def nacl(self, ctx: "MyContext"):
    ...

  @nacl.command("minecraft", aliases=["mc"], help="Run commands in Minecraft")
  async def nacl_minecraft(self, ctx: "MyContext", *, command: str):
    if not self.mcron:
      return await ctx.send(embed=embed(title="Minecraft is not running.", color=MessageColors.ERROR))
    command = "/" + command if "/" not in command else command
    resp = await self.bot.loop.run_in_executor(None, self.mcron.command, command)
    await ctx.send(f"Response\n```json\n{str(resp)}\n```")


def setup(bot):
  bot.add_cog(NaCl(bot))
