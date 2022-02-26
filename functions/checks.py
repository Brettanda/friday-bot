import discord

from typing import TYPE_CHECKING
from discord.ext import commands
# from interactions import Context as SlashContext
from . import exceptions, config
from .custom_contexts import MyContext

if TYPE_CHECKING:
  from discord.ext.commands.core import _CheckDecorator

  from index import Friday as Bot


# def guild_is_tier(tier: str) -> "_CheckDecorator":


def user_is_tier(tier: str) -> "_CheckDecorator":
  async def predicate(ctx: "MyContext") -> bool:
    return True
  return commands.check(predicate)


def is_min_tier(tier: int = config.PremiumTiers.tier_1) -> "_CheckDecorator":
  async def predicate(ctx: "MyContext") -> bool:
    if ctx.author.id == ctx.bot.owner_id:
      return True
    guild = ctx.bot.get_guild(config.support_server_id)
    member = await ctx.bot.get_or_fetch_member(guild, ctx.author.id)
    if member is None:
      raise exceptions.NotInSupportServer()
    if await user_is_min_tier(ctx.bot, member, tier) or await guild_is_min_tier(ctx.bot, ctx.guild, tier):
      return True
    else:
      raise exceptions.RequiredTier()
  return commands.check(predicate)


def guild_is_min_tier(tier: int = config.PremiumTiers.tier_1) -> "_CheckDecorator":
  """ Checks if a guild has at least patreon 'tier' """

  async def predicate(ctx: "MyContext") -> bool:
    if ctx.guild is None:
      return commands.NoPrivateMessage()
    guild_tier = await ctx.pool.fetchval("""SELECT tier FROM patrons WHERE $1 = ANY(patrons.guild_ids) LIMIT 1""", str(ctx.guild.id))
    if guild_tier is None:
      return False
    return guild_tier >= tier
  return commands.check(predicate)


def user_is_min_tier(tier: int = config.PremiumTiers.tier_1) -> "_CheckDecorator":
  """ Checks if a user has at least patreon 'tier' """

  async def predicate(ctx: "MyContext") -> bool:
    pat_cog = ctx.bot.get_cog("Patreons")
    if pat_cog is None:
      return False

    config_ = [p for p in await pat_cog.get_patrons() if p.id == ctx.author.id]
    if len(config_) == 0:
      return False
    return config_[0].tier >= tier
  return commands.check(predicate)


# TODO: Remove this when moved to is_mod_and_min_tier
def is_admin_and_min_tier(tier: int = config.PremiumTiers.tier_1) -> "_CheckDecorator":
  guild_is_min_tier_ = guild_is_min_tier(tier).predicate
  is_admin_ = is_admin().predicate
  user_is_min_tier_ = user_is_min_tier(tier).predicate

  async def predicate(ctx: "MyContext") -> bool:
    try:
      admin = await is_admin_(ctx)
    except Exception:
      admin = False
    if await guild_is_min_tier_(ctx) and (admin or await user_is_min_tier_(ctx)):
      return True
    err = exceptions.RequiredTier("This command requires a premium server and a patron or an admin.")
    err.log = True
    raise err
  return commands.check(predicate)

def is_mod_and_min_tier(*, tier: int = config.PremiumTiers.tier_1, **perms) -> "_CheckDecorator":
  guild_is_min_tier_ = guild_is_min_tier(tier).predicate
  is_mod_or_guild_permissions_ = is_mod_or_guild_permissions(**perms).predicate
  user_is_min_tier_ = user_is_min_tier(tier).predicate

  async def predicate(ctx: "MyContext") -> bool:
    try:
      mod = await is_mod_or_guild_permissions_(ctx)
    except Exception:
      mod = False
    if await guild_is_min_tier_(ctx) and (mod or await user_is_min_tier_(ctx)):
      return True
    err = exceptions.RequiredTier("This command requires a premium server and a patron or a mod.")
    err.log = True
    raise err
  return commands.check(predicate)


def is_supporter() -> "_CheckDecorator":
  """" Checks if the user has the 'is supporting' role that ALL patrons get"""

  async def predicate(ctx: "MyContext") -> bool:
    if ctx.author.id == ctx.bot.owner_id:
      return True
    guild = ctx.bot.get_guild(config.support_server_id)
    member = await ctx.bot.get_or_fetch_member(guild, ctx.author.id)
    if member is None:
      return False
    if await user_is_supporter(ctx.bot, member):
      return True
    else:
      raise exceptions.NotSupporter()
  return commands.check(predicate)


async def user_is_supporter(bot: "Bot", user: discord.User) -> bool:
  if user is None:
    raise exceptions.NotInSupportServer()
  roles = [role.id for role in user.roles]
  if config.patreon_supporting_role not in roles:
    raise exceptions.NotSupporter()
  return True


def is_supporter_or_voted() -> "_CheckDecorator":
  async def predicate(ctx: "MyContext") -> bool:
    support_guild = ctx.bot.get_guild(config.support_server_id)
    member = await ctx.bot.get_or_fetch_member(support_guild, ctx.author.id)
    if member is None:
      return False
    if await user_is_supporter(ctx.bot, member):
      return True
    elif await user_voted(ctx.bot, member):
      return True
    else:
      raise exceptions.NotSupporter()
  return commands.check(predicate)


async def user_voted(bot: "Bot", user: discord.User) -> bool:
  dbl_cog = bot.get_cog("TopGG")
  if dbl_cog is None:
    query = """SELECT id
                FROM reminders
                WHERE event = 'vote'
                AND extra #>> '{args,0}' = $1
                ORDER BY expires
                LIMIT 1;"""
    record = await bot.db.pool.fetchrow(query, str(user.id))
    return True if record else False
  return await dbl_cog.user_has_voted(user.id)


def is_admin() -> "_CheckDecorator":
  """Do you have permission to change the setting of the bot"""
  async def predicate(ctx: "MyContext") -> bool:
    return await commands.is_owner().predicate(ctx) or \
        await commands.has_guild_permissions(manage_guild=True).predicate(ctx) or \
        await commands.has_guild_permissions(administrator=True).predicate(ctx)
  return commands.check(predicate)


def is_mod_or_guild_permissions(**perms) -> "_CheckDecorator":
  """User has a mod role or has the following guild permissions"""
  async def predicate(ctx: "MyContext") -> bool:
    is_owner = await ctx.bot.is_owner(ctx.author)
    if is_owner:
      return True

    if ctx.guild is None:
      return False

    config_cog = ctx.bot.get_cog("Config")
    if config_cog is not None:
      con = await config_cog.get_guild_config(ctx.guild.id)
      if con and any(arole in con.mod_roles for arole in ctx.author.roles):
        return True

    resolved = ctx.author.guild_permissions
    if all(getattr(resolved, name, None) == value for name, value in perms.items()):
      return True
    raise commands.MissingPermissions([name for name, value in perms.items() if getattr(resolved, name, None) != value])

  return commands.check(predicate)


def slash(user: bool = False, private: bool = True) -> "_CheckDecorator":
  # async def predicate(ctx: SlashContext) -> bool:
  #   if user is True and ctx.guild_id and ctx.guild is None and ctx.channel is None:
  #     raise exceptions.OnlySlashCommands()

  #   if not private and not ctx.guild and not ctx.guild_id and ctx.channel_id:
  #     raise commands.NoPrivateMessage()

  #   return True
  # return commands.check(predicate)
  return False
