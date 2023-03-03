from __future__ import annotations

import os
from typing import TYPE_CHECKING

import asyncpg
import discord
from discord.ext import commands

from functions import MessageColors, cache, checks, config, embed
from functions.config import PremiumTiersNew
from functions.custom_contexts import GuildContext

if TYPE_CHECKING:
  from index import Friday
  from typing_extensions import Self
  from functions.custom_contexts import MyContext

CREATOR_TOKEN = os.environ.get("PATREONCREATORTOKEN")


class PatreonButtons(discord.ui.View):
  def __init__(self):
    super().__init__(timeout=None)
    self.add_item(discord.ui.Button(emoji="\N{HANDSHAKE}", label="Support me on Patreon!", style=discord.ButtonStyle.link, url="https://www.patreon.com/join/fridaybot", row=1))


class PatreonConfig:
  __slots__ = ("id", "_current_tier", "_amount_cents", "guild_ids")

  id: int
  _current_tier: int
  _amount_cents: int
  guild_ids: list[int]

  @classmethod
  def from_pledge_record(cls, patron: dict, record: asyncpg.Record) -> Self:
    self = cls()

    self._current_tier = patron["current_tier"]
    self._amount_cents = patron["amount_cents"]
    self.id = int(patron["user_id"], base=10)

    self.guild_ids = record and [int(r, base=10) for r in record["guild_ids"]] or []

    return self

  def __str__(self) -> str:
    return str(self.id)

  def __repr__(self):
    return f"<PatreonConfig id={self.id} tier={self.tier} guilds={len(self.guild_ids)}>"

  @property
  def tier(self) -> int:
    return PremiumTiersNew.from_patreon_tier(self._current_tier).value

  @property
  def max_guilds(self) -> int:
    if self.tier >= PremiumTiersNew.tier_2.value:
      return 1
    return 0

  @property
  def guilds_remaining(self) -> int:
    return self.max_guilds - len(self.guild_ids)


class Patreons(commands.Cog):
  """Exlusive commands for Friday's Patrons"""

  def __init__(self, bot: Friday) -> None:
    self.bot: Friday = bot
    self.owner_patroned: config.PremiumTiersNew = config.PremiumTiersNew.free

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @cache.cache()
  async def get_patrons(self) -> list[PatreonConfig]:
    conn = self.bot.pool

    # available options to return ?include=currently_entitled_tiers,address&fields[member]=full_name,is_follower,last_charge_date,last_charge_status,lifetime_support_cents,currently_entitled_amount_cents,patron_status&fields[tier]=amount_cents,created_at,description,discord_role_ids,edited_at,patron_count,published,published_at,requires_shipping,title,url&fields[address]=addressee,city,line_1,line_2,phone_number,postal_code,state
    # can also be found here https://docs.patreon.com/#get-api-oauth2-v2-campaigns-campaign_id-members
    s = 'campaigns/5362911/members?include=currently_entitled_tiers,user&fields[user]=url,social_connections&fields[member]=full_name,currently_entitled_amount_cents,patron_status&fields[tier]=amount_cents,discord_role_ids,published_at,requires_shipping,title,url'
    response = await self.bot.session.get(
        "https://www.patreon.com/api/oauth2/v2/{}".format(s),
        headers={
              'Authorization': "Bearer {}".format(CREATOR_TOKEN),
              'User-Agent': 'Patreon-Python, version 0.5.0, platform Linux-5.10.102.1-microsoft-standard-WSL2-x86_64-with-glibc2.29',

        })
    resp = await response.json()

    members: list[dict] = []
    for shit in resp['data']:
      if shit['attributes']['patron_status'] != 'active_patron':
        continue
      r = {
          "current_tier": shit["relationships"]["currently_entitled_tiers"]['data'][0]["id"],
          "amount_cents": shit['attributes']['currently_entitled_amount_cents'],
      }
      for i in resp['included']:
        if i['id'] == shit['relationships']['user']['data']['id']:
          r['user_id'] = i['attributes']['social_connections']['discord']['user_id']
      members.append(r)
    # # me is patron
    if self.owner_patroned >= config.PremiumTiersNew.tier_1:
      members.append({"current_tier": str(self.owner_patroned.patreon_tier), "amount_cents": "150", "user_id": "215227961048170496"})

    query = "SELECT * FROM patrons"
    records = await conn.fetch(query)

    configs = []
    for p in members:
      record = next((r for r in records if r["user_id"] == p["user_id"]), None)
      configs.append(PatreonConfig.from_pledge_record(p, record))

    return configs

  async def cog_after_invoke(self, ctx: MyContext):
    self.get_patrons.invalidate(self)
    if ctx.guild is None:
      return
    self.bot.dispatch("invalidate_patreon", ctx.guild.id)

  @commands.group(name="patreon", aliases=["patron"], invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  async def norm_patreon(self, ctx: GuildContext):
    """Commands for Friday's Patrons"""
    await ctx.send(embed=embed(
        title="Become a Patron!",
        description="Become a Patron and get access to awesome features.\n\nYou can view all of the available features on Patreon.\n\nA few of the features that you will get access include:",
        fieldstitle=["Better Rate-limiting", "Personas", "Cool role(s)", "Priority Support", "And more"],
        fieldsval=["100 messages/12 hours instead of 30 messages/12 hours.", "Change the persona that Friday uses when chatting in your server", "You will be granted role(s) in the support server.", "Get priority support for your encounters with Friday", "Get the full list of benefits on Patreon."],
        fieldsin=[False] * 5,
        footer="For the full list of patreon commands type `!help patreon`",
    ),
        view=PatreonButtons())

  @norm_patreon.command("owner")
  @commands.is_owner()
  async def patreon_owner(self, ctx: MyContext, tier: int = config.PremiumTiersNew.free.value):
    self.owner_patroned = config.PremiumTiersNew(tier)
    self.get_patrons.invalidate(self)
    await ctx.send(f"You are '{self.owner_patroned}' a patron")

  @norm_patreon.command("activate", aliases=["update"])
  async def patreon_update(self, ctx: MyContext):
    """Run this command to activate your Patronage or update your Patreon tier."""
    self.get_patrons.invalidate(self)
    if ctx.guild is not None:
      self.bot.dispatch("invalidate_patreon", ctx.guild.id)

    await ctx.send(embed=embed(title="The patrons list has been updated!", description="If you still don't have access to Patroned features, please contact the developer on the support server."))

  @norm_patreon.command("status")
  async def patreon_status(self, ctx: MyContext):
    """Updates Friday to recognize your Patreon tier and guilds."""
    patrons = await self.get_patrons()

    if ctx.author.id not in [p.id for p in patrons]:
      return await ctx.send(embed=embed(
          title="Your Patronage could not be found",
          description=f"Your Discord account could not be found in Patreon list.\n\nPlease check that you have your Patreon account connected to Discord.\n\n**If you have completed the above and still have not recieved your benifits then please contact the developer on the support server `{ctx.clean_prefix}support`**",
          color=MessageColors.error())
      )

    patron = next(p for p in patrons if p.id == ctx.author.id)

    statuses = {
        "connected_discord": ":white_check_mark:" if bool(ctx.author.id in [p.id for p in patrons]) else ":x:",
        "activated_server_ids": ', '.join([str(i) for i in patron.guild_ids]) if len(patron.guild_ids) > 0 else ":x:",
        "current_server_activated": ":white_check_mark:" if bool(ctx.guild and ctx.guild.id in patron.guild_ids) else ":x:",
        # Add guilds remaining
    }

    await ctx.send(embed=embed(
        title="Your Patreon Status",
        description=f"**Connected Discord Account**: {statuses['connected_discord']}\n**Activated Server ID(s)**: {statuses['activated_server_ids']}\n**Current Server Activated**: {statuses['current_server_activated']}"
    ))

  @norm_patreon.group("server", invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  async def norm_patreon_server(self, ctx: MyContext):
    """Activate the server that you would like to apply your patronage to"""
    await ctx.send_help(ctx.command)

  @norm_patreon_server.command("activate")
  @commands.guild_only()
  @checks.user_is_min_tier(tier=config.PremiumTiersNew.tier_2)
  async def norm_patreon_server_true(self, ctx: GuildContext):
    async with ctx.typing():
      con = next((c for c in await self.get_patrons() if str(c) == str(ctx.author.id)), None)

    if not con or con.id != ctx.author.id:
      return await ctx.send(embed=embed(title="Your Patronage was not found", color=MessageColors.error()))

    if con and con.tier <= config.PremiumTiersNew.tier_1.value and con.guilds_remaining <= 0:
      guilds = []
      for g in con.guild_ids:
        guild = self.bot.get_guild(g)
        if guild is None:
          guild = await self.bot.fetch_guild(g)
        guilds.append(guild or g)

      guild_names = [f"`{g.name if not isinstance(g, int) else None}` (ID: {g if isinstance(g, int) else g.id})" for g in guilds]
      return await ctx.send(embed=embed(title=f"You can only activate {con.max_guilds} server{'s' if con.max_guilds > 1 else ''}", description=f"The server{'s' if con.max_guilds > 1 else ''} you already have activated {'are' if con.max_guilds > 1 else 'is'}:\n\n" + '\n'.join(guild_names), color=MessageColors.error()))

    query = "INSERT INTO patrons (user_id,guild_ids) VALUES ($1,array[$2]::text[]) ON CONFLICT (user_id) DO UPDATE SET guild_ids=array_append(patrons.guild_ids,$2) WHERE NOT ($2=any(patrons.guild_ids));"
    await ctx.db.execute(query, str(ctx.author.id), str(ctx.guild.id))
    await ctx.send(embed=embed(title="You have upgraded this server to premium"))

  @norm_patreon_server.command("deactivate")
  @commands.guild_only()
  @checks.is_mod_and_min_tier(tier=config.PremiumTiersNew.tier_1, manage_guild=True)
  async def norm_patreon_server_false(self, ctx: GuildContext):
    query = "SELECT guild_ids FROM patrons WHERE user_id = $1;"
    record = await ctx.db.fetchval(query, str(ctx.author.id))
    if not record:
      return await ctx.send(embed=embed(title="This is not a premium server", color=MessageColors.error()))

    if len(record) == 0:
      return await ctx.send(embed=embed(title="You don't have any premium server activated", color=MessageColors.error()))

    query = "UPDATE patrons SET guild_ids=array_remove(patrons.guild_ids,$1) WHERE user_id=$2 AND ($1=ANY(patrons.guild_ids));"
    await ctx.db.execute(query, str(ctx.guild.id), str(ctx.author.id))
    await ctx.send(embed=embed(title="You have successfully removed your server"))


async def setup(bot):
  await bot.add_cog(Patreons(bot))
