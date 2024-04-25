# import asyncio
# import os
# from typing import Optional

# import discord
# from discord.ext import commands
# from typing import TYPE_CHECKING

# from functions import MyContext, embed, cache  # , queryIntents

# from .log import CustomWebhook

# if TYPE_CHECKING:
#   from index import Friday as Bot


# class FunnyOrNah(discord.ui.View):
#   def __init__(self, *, timeout: float, author_id: int, ctx: MyContext) -> None:
#     super().__init__(timeout=timeout)
#     self.value: Optional[bool] = None
#     self.author_id: int = author_id
#     self.ctx: MyContext = ctx
#     self.message: Optional[discord.Message] = None

#   async def interaction_check(self, interaction: discord.Interaction) -> bool:
#     if interaction.user and interaction.user.id == self.author_id:
#       return True
#     else:
#       await interaction.response.send_message('This confirmation dialog is not for you.', ephemeral=True)
#       return False

#   async def on_timeout(self) -> None:
#     try:
#       await self.message.edit(view=None)
#     except discord.NotFound:
#       pass

#   @discord.ui.button(emoji="\N{ROLLING ON THE FLOOR LAUGHING}", label='Funny', custom_id="funny-funny", style=discord.ButtonStyle.green)
#   async def funny(self, button: discord.ui.Button, interaction: discord.Interaction):
#     self.value = True
#     await interaction.response.defer()
#     await interaction.edit_original_response(view=None)
#     await interaction.followup.send("Thank you for improving the bot!", ephemeral=True)
#     self.stop()

#   @discord.ui.button(emoji="\N{YAWNING FACE}", label='Not funny', custom_id="funny-nah", style=discord.ButtonStyle.red)
#   async def nah(self, button: discord.ui.Button, interaction: discord.Interaction):
#     self.value = False
#     await interaction.response.defer()
#     await interaction.delete_original_response()
#     await interaction.followup.send("Thank you for improving the bot!", ephemeral=True)
#     self.stop()


# class Config:
#   @classmethod
#   async def from_record(cls, record, bot):
#     self = cls()

#     self.bot = bot
#     self.id: int = int(record["id"], base=10)
#     self.enabled: bool = bool(record["toyst_enabled"])
#     return self


# class TOYST(commands.Cog):
#   def __init__(self, bot: "Bot"):
#     self.bot = bot
#     self.lock = asyncio.Lock()

#   def __repr__(self) -> str:
#     return f"<cogs.{self.__cog_name__}>"

#   @discord.utils.cached_property
#   def log_new_toyst(self) -> CustomWebhook:
#     return CustomWebhook.partial(os.environ.get("WEBHOOKNEWTOYSTID"), os.environ.get("WEBHOOKNEWTOYSTTOKEN"), session=self.bot.session)

#   @cache.cache()
#   async def get_guild_config(self, guild_id: int) -> Optional[Config]:
#     query = "SELECT * FROM servers WHERE id=$1 LIMIT 1;"
#     async with self.bot.pool.acquire(timeout=300.0) as conn:
#       record = await conn.fetchrow(query, str(guild_id))
#       self.bot.logger.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}")
#       if record is not None:
#         return await Config.from_record(record, self.bot)
#       return None

#   @commands.Cog.listener()
#   async def on_message(self, msg: discord.Message) -> None:
#     await self.bot.wait_until_ready()

#     if msg.guild is None:
#       return

#     if msg.author.bot:
#       return

#     if len(msg.clean_content) == 0 or len(msg.clean_content) > 200:
#       return

#     if msg.guild.id in self.bot.blacklist or msg.author.id in self.bot.blacklist:
#       return

#     ctx = await self.bot.get_context(msg, cls=MyContext)
#     if ctx.command is not None:
#       return

#     result, intent, chance, inbag, incomingContext, outgoingContext, sentiment = await queryIntents.classify_local(msg.clean_content)

#     if msg.content == "s":
#       view = FunnyOrNah(timeout=20, author_id=msg.author.id, ctx=ctx)
#       view.message = await msg.reply(embed=embed(title="something poggers"), view=view)
#       await view.wait()
#       if view.value:
#         await self.log_new_toyst.safe_send(embed=embed(title="This was funny", description=msg.clean_content))


async def setup(bot):
  ...
  # await bot.add_cog(TOYST(bot))
