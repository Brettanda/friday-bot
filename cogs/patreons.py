import functools
import os

import patreon
from discord.ext import commands
import discord
from typing_extensions import TYPE_CHECKING

from functions import MessageColors, MyContext, config, embed, cache, checks

if TYPE_CHECKING:
  from index import Friday as Bot

CREATOR_TOKEN = os.environ.get("PATREONCREATORTOKEN")


class PatreonButtons(discord.ui.View):
  def __init__(self):
    super().__init__(timeout=None)
    self.add_item(discord.ui.Button(emoji="\N{HANDSHAKE}", label="Support me on Patreon!", style=discord.ButtonStyle.link, url="https://www.patreon.com/join/fridaybot", row=1))


class PatreonConfig:
  def __init__(self):
    self.id: int = None
    self._tier: int = None
    self._amount_cents: int = None
    self.declined_since = None
    self.guild_ids: list = None

  @classmethod
  def from_pledge_record(cls, pledge: patreon.jsonapi.parser.JSONAPIResource, record):
    self = cls()

    self.declined_since = pledge.relationship("patron").attribute("declined_since")
    self._amount_cents = pledge.relationship("reward").attribute("amount_cents")
    self.id = int(pledge.relationship("patron").attribute("social_connections")["discord"]["user_id"], base=10)

    self._tier = record["tier"] if record else None
    self.guild_ids = record["guild_ids"] if record else []

    return self

  def __str__(self) -> str:
    return str(self.id)

  def __repr__(self):
    return f"<PatreonConfig id={self.id} tier={self.tier} guilds={len(self.guild_ids)}>"

  def __hash__(self):
    return hash(self.id, self.tier, *self.guild_ids)

  @property
  def tier(self) -> int:
    if self._tier:
      return self._tier
    if self._amount_cents >= 500:
      return config.PremiumTiersNew.tier_1.value

  @property
  def max_guilds(self) -> int:
    # TODO: Make this dynamic with the tiers
    return 1

  @property
  def guilds_remaining(self) -> int:
    return self.max_guilds - len(self.guild_ids)

  @property
  def max_chat_characters(self) -> int:
    # TODO: Make this dynamic with the tiers
    return 200

  @property
  def max_chat_history(self) -> int:
    # TODO: Make this dynamic with the tiers
    return 6


class Patreons(commands.Cog):
  """Exlusive command for Friday's Patreon Patrons"""

  def __init__(self, bot: "Bot") -> None:
    self.bot = bot
    self.patreon = patreon.API(CREATOR_TOKEN)

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @cache.cache()
  async def get_patrons(self) -> list:
    campaign = await self.bot.loop.run_in_executor(None, self.patreon.fetch_campaign)
    campaign_id = campaign.data()[0].id()

    all_pledges = []
    cursor = None
    # https://www.youtube.com/watch?v=RO6JxDOVwLQ
    while True:
      fetch = functools.partial(self.patreon.fetch_page_of_pledges, cursor=cursor, fields={"pledge": ["total_historical_amount_cents", "declined_since"]})
      pledges_response = await self.bot.loop.run_in_executor(None, fetch, campaign_id, 25)
      cursor = self.patreon.extract_cursor(pledges_response)
      all_pledges += pledges_response.data()
      if cursor is None:
        break

    query = "SELECT * FROM patrons"
    records = await self.bot.pool.fetch(query)

    configs = []
    for p in all_pledges:
      record = next((r for r in records if r["user_id"] == p.relationship("patron").attribute("social_connections")["discord"]["user_id"]), None)
      configs.append(PatreonConfig.from_pledge_record(p, record))

    return configs

  async def cog_after_invoke(self, ctx: "MyContext"):
    self.get_patrons.invalidate(self)
    if ctx.guild is None:
      return
    self.bot.dispatch("invalidate_patreon", ctx.guild.id)

  @commands.group(name="patreon", aliases=["patron"], help="Commands for Friday's Patrons", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  async def norm_patreon(self, ctx: "MyContext"):
    await ctx.send(embed=embed(
        title="Become a Patron!",
        description="Become a Patron and get access to awesome features.\n\nYou can view all of the available features on Patreon.\n\nA few of the features that you will get access include:",
        fieldstitle=["Better Rate-limiting", "Personas", "Cool role(s)", "Priority Support"],
        fieldsval=["100 messages/12 hours instead of 30 messages/12 hours.", "Change the persona that Friday uses when chatting in your server", "You will be granted role(s) in the support server.", "Get priority support for your encounters with Friday"],
        fieldsin=[False] * 4,
        footer="For the full list of patreon commands type `!help patreon`",
    ),
        view=PatreonButtons())

  @norm_patreon.command("activate", aliases=["update"], help="Run this command to activate your Patronage or update your Patreon tier.")
  async def patreon_update(self, ctx: "MyContext"):
    self.get_patrons.invalidate(self)
    if ctx.guild is not None:
      self.bot.dispatch("invalidate_patreon", ctx.guild.id)

    await ctx.send(embed=embed(title="The patrons list has been updated!", description="If you still don't have access to Patroned features, please contact the developer on the support server."))

  @norm_patreon.command("status", description="Updates Friday to recognize your Patreon tier and guilds.")
  async def patreon_status(self, ctx: "MyContext"):
    patrons = await self.get_patrons()

    if ctx.author.id not in [p.id for p in patrons]:
      return await ctx.send(embed=embed(
          title="Your Patronage could not be found",
          description=f"Your Discord account could not be found in Patreon list.\n\nPlease check that you have your Patreon account connected to Discord.\n\n**If you have completed the above and still have not recieved your benifits then please contact the developer on the support server `{ctx.clean_prefix}support`**",
          color=MessageColors.ERROR)
      )

    patron = next(p for p in patrons if p.id == ctx.author.id)

    statuses = {
        "connected_discord": ":white_check_mark:" if bool(ctx.author.id in [p.id for p in patrons]) else ":x:",
        "activated_server_ids": ', '.join(patron.guild_ids) if len(patron.guild_ids) > 0 else ":x:",
        "current_server_activated": ":white_check_mark:" if bool(ctx.guild and ctx.guild.id in [int(item, base=10) for item in patron.guild_ids]) else ":x:",
        # Add guilds remaining
    }

    await ctx.send(embed=embed(
        title="Your Patreon Status",
        description=f"**Connected Discord Account**: {statuses['connected_discord']}\n**Activated Server ID(s)**: {statuses['activated_server_ids']}\n**Current Server Activated**: {statuses['current_server_activated']}"
    ))

  @norm_patreon.group("server", help="Activate the server that you would like to apply your patronage to", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  async def norm_patreon_server(self, ctx: "MyContext"):
    await ctx.send_help(ctx.command)

  @norm_patreon_server.command("activate")
  @commands.guild_only()
  async def norm_patreon_server_true(self, ctx: "MyContext"):
    async with ctx.typing():
      con = next((c for c in await self.get_patrons() if str(c) == str(ctx.author.id)), None)

    if not con or con.id != ctx.author.id:
      return await ctx.send(embed=embed(title="Your Patronage was not found", color=MessageColors.ERROR))

    if con and con.tier <= config.PremiumTiersNew.tier_1.value and con.guilds_remaining <= 0:
      guilds = [int(g, base=10) for g in con.guild_ids]
      for g in con.guild_ids:
        guild = self.bot.get_guild(g)
        if guild is None:
          guild = await self.bot.fetch_guild(g)
        guilds[guilds.index(int(g, base=10))] = guild

      guild_names = [f"`{g.name if not isinstance(g, int) else None}` (ID: {g if isinstance(g, int) else g.id})" for g in guilds]
      return await ctx.send(embed=embed(title=f"You can only activate {con.max_guilds} server{'s' if con.max_guilds > 1 else ''}", description=f"The server{'s' if con.max_guilds > 1 else ''} you already have activated {'are' if con.max_guilds > 1 else 'is'}:\n\n" + '\n'.join(guild_names), color=MessageColors.ERROR))

    query = f"INSERT INTO patrons (user_id,tier,guild_ids) VALUES ($1,{config.PremiumTiersNew.tier_1.value},array[$2]::text[]) ON CONFLICT (user_id) DO UPDATE SET guild_ids=array_append(patrons.guild_ids,$2) WHERE NOT ($2=any(patrons.guild_ids));"
    await ctx.db.execute(query, str(ctx.author.id), str(ctx.guild.id))
    await ctx.send(embed=embed(title="You have upgraded this server to premium"))

  @norm_patreon_server.command("deactivate", aliases=["de-activate"])
  @commands.guild_only()
  @checks.is_mod_and_min_tier(tier=config.PremiumTiersNew.tier_1.value, manage_guild=True)
  async def norm_patreon_server_false(self, ctx: "MyContext"):
    query = "SELECT guild_ids FROM patrons WHERE user_id = $1;"
    record = await ctx.db.fetchval(query, str(ctx.author.id))
    if not record:
      return await ctx.send(embed=embed(title="This is not a premium server", color=MessageColors.ERROR))

    if len(record) == 0:
      return await ctx.send(embed=embed(title="You don't have any premium server activated", color=MessageColors.ERROR))

    query = "UPDATE patrons SET guild_ids=array_remove(patrons.guild_ids,$1) WHERE user_id=$2 AND ($1=ANY(patrons.guild_ids));"
    await ctx.db.execute(query, str(ctx.guild.id), str(ctx.author.id))
    await ctx.send(embed=embed(title="You have successfully removed your server"))


def setup(bot):
  bot.add_cog(Patreons(bot))
