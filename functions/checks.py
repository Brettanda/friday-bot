import discord

from typing import TYPE_CHECKING, Union
from discord.ext import commands
# from interactions import Context as SlashContext
from . import exceptions, config
from .custom_contexts import MyContext

if TYPE_CHECKING:
  from discord.ext.commands.core import _CheckDecorator

  from index import Friday as Bot


async def min_tiers(bot: "Bot", msg: discord.Message) -> tuple:
  guild = bot.get_guild(config.support_server_id)
  member = await bot.get_or_fetch_member(guild, msg.author.id)
  voted, t1_user, t1_guild = await user_voted(bot, member), await user_is_min_tier(bot, member, config.PremiumTiers.tier_1), await guild_is_min_tier(bot, guild, config.PremiumTiers.tier_1)
  if t1_user or t1_guild:
    return (voted, t1_user, t1_guild, t1_user, t1_guild, t1_user, t1_guild, t1_user, t1_guild)
  t2_user, t2_guild = await user_is_min_tier(bot, member, config.PremiumTiers.tier_2), await guild_is_min_tier(bot, guild, config.PremiumTiers.tier_2)
  if t2_user or t2_guild:
    return (voted, t1_user, t1_guild, t2_user, t2_guild, t2_user, t2_guild, t2_user, t2_guild)
  t3_user, t3_guild = await user_is_min_tier(bot, member, config.PremiumTiers.tier_3), await guild_is_min_tier(bot, guild, config.PremiumTiers.tier_3)
  if t3_user or t3_guild:
    return (voted, t1_user, t1_guild, t2_user, t2_guild, t3_user, t3_guild, t3_user, t3_guild)
  t4_user, t4_guild = await user_is_min_tier(bot, member, config.PremiumTiers.tier_4), await guild_is_min_tier(bot, guild, config.PremiumTiers.tier_4)
  if t4_user or t4_guild:
    return (voted, t1_user, t1_guild, t2_user, t2_guild, t3_user, t3_guild, t4_user, t4_guild)
  return (voted, False, False, False, False, False, False, False, False)

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
  user_id = await bot.db.query("SELECT id FROM votes WHERE id=$1", str(user.id))
  if isinstance(user_id, list) and len(user_id) > 0:
    user_id = user_id[0]
  elif isinstance(user_id, list) and len(user_id) == 0:
    user_id = None
  return True if user_id is not None else False


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
