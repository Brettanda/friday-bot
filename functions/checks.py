import discord

from typing import TYPE_CHECKING, Union
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


async def guild_is_min_tier(bot: "Bot", guild: discord.Guild, tier: int = config.PremiumTiers.tier_1) -> bool:
  """ Checks if a guild has at least patreon 'tier' """

  if guild is None:
    return commands.NoPrivateMessage()
  guild_tier = await bot.db.query("""SELECT tier FROM patrons WHERE guild_id=$1 LIMIT 1""", str(guild.id))
  if guild_tier is None:
    return False
  return guild_tier >= tier


async def user_is_min_tier(bot: "Bot", user: Union[discord.User, discord.Member], tier: int = config.PremiumTiers.tier_1) -> bool:
  """ Checks if a user has at least patreon 'tier' """

  if not isinstance(user, discord.Member) or (hasattr(user, "guild") and user.guild.id != config.support_server_id or not hasattr(user, "guild")):
    guild = bot.get_guild(config.support_server_id)
    user = await bot.get_or_fetch_member(guild, user.id)
    if user is None:
      raise exceptions.NotInSupportServer()
  # if not hasattr(user, "guild"):
  #   return False
  roles = [role.id for role in user.roles]
  if config.PremiumTiers().get_role(tier) in roles:
    return True
  for i in range(tier, len(config.PremiumTiers.roles) - 1):
    role = bot.get_guild(config.support_server_id).get_role(config.PremiumTiers().get_role(i))
    if role.id in roles:
      return True
  return False


def is_supporter() -> "_CheckDecorator":
  """" Checks if the user has the 'is supporting' role that ALL patrons get"""

  async def predicate(ctx: "MyContext") -> bool:
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
  query = """SELECT id
              FROM reminders
              WHERE event = 'vote'
              AND extra #>> '{args,0}' = $1
              ORDER BY expires
              LIMIT 1;"""
  record = await bot.db.pool.fetchrow(query, str(user.id))
  return True if record else False


def is_admin() -> "_CheckDecorator":
  """Do you have permission to change the setting of the bot"""
  return commands.check_any(
      commands.is_owner(),
      commands.has_guild_permissions(manage_guild=True),
      commands.has_guild_permissions(administrator=True))


def slash(user: bool = False, private: bool = True) -> "_CheckDecorator":
  # async def predicate(ctx: SlashContext) -> bool:
  #   if user is True and ctx.guild_id and ctx.guild is None and ctx.channel is None:
  #     raise exceptions.OnlySlashCommands()

  #   if not private and not ctx.guild and not ctx.guild_id and ctx.channel_id:
  #     raise commands.NoPrivateMessage()

  #   return True
  # return commands.check(predicate)
  return False
