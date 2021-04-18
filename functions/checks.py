import discord
from discord.ext import commands
from discord_slash import SlashContext


def bot_has_guild_permissions(**perms):
  invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
  if invalid:
    raise TypeError(f"Invalid permssion(s): {', '.join(invalid)}")

  async def predicate(ctx: commands.Context or SlashContext):
    if not ctx.guild:
      raise commands.NoPrivateMessage()

    current_permissions = ctx.guild.me.guild_permissions
    missing = [perm for perm, value in perms.items() if getattr(current_permissions, perm) != value]

    if not missing:
      return True

    raise commands.BotMissingPermissions(missing)
  return commands.check(predicate)
