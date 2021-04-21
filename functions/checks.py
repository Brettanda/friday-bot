import discord
from discord.ext import commands
from discord_slash import SlashContext
from functions import exceptions


def bot_has_guild_permissions(**perms):
  invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
  if invalid:
    raise TypeError(f"Invalid permssion(s): {', '.join(invalid)}")

  async def predicate(ctx: commands.Context or SlashContext):
    if not ctx.guild and not ctx.guild_id:
      raise commands.NoPrivateMessage()

    guild = ctx.guild if not ctx.guild else (ctx.bot.get_guild(ctx.guild_id))

    current_permissions = ctx.guild.me.guild_permissions
    missing = [perm for perm, value in perms.items() if getattr(current_permissions, perm) != value]

    if not missing:
      return True

    raise commands.BotMissingPermissions(missing)
  return commands.check(predicate)


def slash(user: bool = False, private: bool = True):
  async def predicate(ctx: SlashContext):
    if user is True and ctx.guild_id and ctx.guild is None and ctx.channel is None:
      raise exceptions.OnlySlashCommands()

    if not private and not ctx.guild and not ctx.guild_id and ctx.channel_id:
      raise commands.NoPrivateMessage()

    return True
  return commands.check(predicate)


# def bot_has_permissions(**perms):
#   invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
#   if invalid:
#     raise TypeError(f"Invalid permission(s): {', '.join(invalid)}")

#   async def predicate(ctx:commands.Context or SlashContext):
#     if not ctx.guild and not ctx.guild_id:
#       raise commands.NoPrivateMessage()

#     channel = ctx.channel if ctx.channel is not None else ctx.bot.get_channel(ctx.channel_id)

#     current_permissions = ctx.channel

#   return commands.check(predicate)
