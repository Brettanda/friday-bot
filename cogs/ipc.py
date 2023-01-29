from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional
# from discord.ext import commands
# from discord.ext.ipc import Server
# from discord.ext.ipc.errors import IPCError

if TYPE_CHECKING:
  from index import Friday

log = logging.getLogger(__name__)


# class IPC(commands.Cog):
#   ipc: Server

#   def __init__(self, bot: Friday):
#     self.bot: Friday = bot

#   def __repr__(self) -> str:
#     return f"<cogs.{self.__cog_name__}>"

#   # async def cog_load(self) -> None:
#   #   self.ipc = Server(
#   #       self.bot,
#   #       port=self.bot._port,
#   #       do_multicast=True,
#   #       multicast_port=self.bot._multicast_port,
#   #       secret_key=self.bot._key,
#   #       logger=log)
#   #   self.ipc.start()

#   @commands.Cog.listener()
#   async def on_ipc_ready(self):
#     log.info("Ipc is ready")

#   @commands.Cog.listener()
#   async def on_ipc_error(self, endpoint: str, error: IPCError):
#     log.error(endpoint, "raised", error, exc_info=(type(error), error, error.__traceback__))

#   # @route
#   # async def get_user_data(self, data: dict):
#   #   user = self.bot.get_user(data.user_id)
#   #   return user._to_minimal_user_json()  # THE OUTPUT MUST BE JSON SERIALIZABLE!


async def setup(bot):
  ...
  # await bot.add_cog(IPC(bot))
