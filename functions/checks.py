import discord

from typing import TYPE_CHECKING
from discord.ext import commands
from discord_slash import SlashContext
from functions import exceptions, config

if TYPE_CHECKING:
  from discord.ext.commands.core import _CheckDecorator

  from index import Friday as Bot

# def guild_is_tier(tier: str) -> "_CheckDecorator":


def user_is_tier(tier: str) -> "_CheckDecorator":
  async def predicate(ctx) -> bool:
    return True
  return commands.check(predicate)


def is_min_tier(tier: str) -> "_CheckDecorator":
  tier_level = config.premium_tiers.get(tier, None)
  if tier_level is None:
    raise TypeError(f"Invalid tier name: {tier}")

  async def predicate(ctx) -> bool:
    if ctx.author.id == ctx.bot.owner_id:
      return True
    member = None
    try:
      member = await ctx.bot.get_guild(config.support_server_id).fetch_member(ctx.author.id)
    except discord.HTTPException:
      raise exceptions.NotInSupportServer()
    if await user_is_min_tier(ctx.bot, member, tier):
      return True
    elif await guild_is_min_tier(ctx.bot, ctx.guild, tier):
      return True
    else:
      raise exceptions.RequiredTier()
  return commands.check(predicate)


async def guild_is_min_tier(bot: "Bot", guild: discord.Guild, tier: str) -> bool:
  """ Checks if a guild has at least patreon 'tier' """

  # FIXME: reee
  # if not ctx.guild:
  #   raise commands.NoPrivateMessage()
  if guild is None:
    return False
  guild_tier = bot.get_guild_tier(guild)
  tier_level = config.premium_tiers[tier]
  if guild_tier in list(config.premium_tiers)[tier_level:]:
    return True
  return False
  # raise exceptions.RequiredTier()
  return True


async def user_is_min_tier(bot: "Bot", user: discord.User, tier: str) -> bool:
  """ Checks if a user has at least patreon 'tier' """

  if user.guild and user.guild.id != config.support_server_id:
    user = None
    try:
      user = await bot.get_guild(config.support_server_id).fetch_member(user.id)
    except Exception:
      return False
  if not hasattr(user, "guild"):
    return False
  roles = [role.id for role in user.roles]
  if config.patreon_supporting_role not in roles:
    return False
    # raise exceptions.NotSupporter()
  if config.premium_roles[tier] in roles:
    return True
  tier_level = config.premium_tiers[tier]
  for i in range(tier_level, len(config.premium_tiers) - 1):
    role = bot.get_guild(config.support_server_id).get_role(config.premium_roles[i])
    if role.id in roles:
      return True


def is_supporter() -> "_CheckDecorator":
  """" Checks if the user has the 'is supporting' role that ALL patrons get"""

  async def predicate(ctx) -> bool:
    member = await ctx.bot.get_guild(config.support_server_id).fetch_member(ctx.author.id)
    if await user_is_supporter(ctx.bot, member):
      return True
    else:
      raise exceptions.NotSupporter()
  return commands.check(predicate)


async def user_is_supporter(bot: "Bot", user: discord.User) -> bool:
  if user is None:
    raise exceptions.NotInSupportServer()
  roles = [role.id for role in user.roles]
  if user.id == bot.owner_id or config.premium_roles["friends"] in roles:
    return True
  if config.patreon_supporting_role not in roles:
    raise exceptions.NotSupporter()
  return True


def bot_has_guild_permissions(**perms) -> "_CheckDecorator":
  invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
  if invalid:
    raise TypeError(f"Invalid permssion(s): {', '.join(invalid)}")

  async def predicate(ctx: commands.Context or SlashContext) -> bool:
    if not ctx.guild and ctx.guild_id:
      raise commands.NoPrivateMessage()

    # guild = ctx.guild if not ctx.guild else (ctx.bot.get_guild(ctx.guild_id))

    current_permissions = ctx.guild.me.guild_permissions
    missing = [perm for perm, value in perms.items() if getattr(current_permissions, perm) != value]

    if not missing:
      return True

    raise commands.BotMissingPermissions(missing)
  return commands.check(predicate)


def slash(user: bool = False, private: bool = True) -> "_CheckDecorator":
  async def predicate(ctx: SlashContext) -> bool:
    if user is True and ctx.guild_id and ctx.guild is None and ctx.channel is None:
      raise exceptions.OnlySlashCommands()

    if not private and not ctx.guild and not ctx.guild_id and ctx.channel_id:
      raise commands.NoPrivateMessage()

    return True
  return commands.check(predicate)


# def bot_has_permissions(**perms) -> "_CheckDecorator":
#   invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
#   if invalid:
#     raise TypeError(f"Invalid permission(s): {', '.join(invalid)}")

#   async def predicate(ctx:commands.Context or SlashContext) -> bool:
#     if not ctx.guild and not ctx.guild_id:
#       raise commands.NoPrivateMessage()

#     channel = ctx.channel if ctx.channel is not None else ctx.bot.get_channel(ctx.channel_id)

#     current_permissions = ctx.channel

#   return commands.check(predicate)
