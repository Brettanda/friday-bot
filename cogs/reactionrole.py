import asyncio

import discord
from discord.ext import commands

# from cogs.cleanup import get_delete_time
from functions import embed


class ReactionRole(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.msgs = {}

  def cog_check(self, ctx):
    if ctx.guild is None:
      raise commands.NoPrivateMessage("This command can only be used within a guild")
    return True

  # @commands.group(name="reactionrole",aliases=["rr"],hidden=True,invoke_without_command=True)
  # @commands.is_owner()
  # @commands.has_guild_permissions(manage_roles=True)
  # @commands.bot_has_guild_permissions(manage_roles=True)
  # async def reaction_role(self,ctx):
  #   send_help = await cmd_help(ctx,ctx.command)
  #   await ctx.message.delete(delay=await get_delete_time(ctx))
    # await send_help.delete(delay=await get_delete_time(ctx))
  # async def reactionrole(self,ctx,message:discord.Message,*reactions_roles:str):
  #   reactions_roles = list(reactions_roles)
  #   x = 0
  #   for item in reactions_roles:
  #     item = item.split(";;")
  #     item[1] = "".join(item[1].split("<@&"))
  #     item[1] = "".join(item[1].split(">"))
  #     # item[1] = "".join(item[1].split(","))
  #     # item[1] = int("".join(item[1].split(")")))
  #     print(item[1])
  #     reactions_roles[x] = [item[0],ctx.guild.get_role(int(item[1]))]
  #     x = x + 1
  #   print(reactions_roles)

  #   for emoji in reactions_roles:
  #     emoji = emoji[0]
  #     await message.add_reaction(f"{emoji}")

  #   await ctx.reply(embed=embed(title=f"{message.jump_url} is a new reaction role message"))

  # {message_id:{"🔗":role_id,"😈":role_id}}

  # @reaction_role.command(name="start",aliases=["setup"],hidden=True)
  # @commands.is_owner()
  # @commands.has_guild_permissions(manage_roles=True)
  # @commands.bot_has_guild_permissions(manage_roles=True)
  # async def reaction_start(self,ctx,*,title:str=""):
  #   msg = await ctx.channel.send(embed=embed(title=title))
  #   self.msgs.update({ctx.channel.id:{"id":msg.id,"title":title,"description":"","footer":"","reactions":[]}})
  #   await ctx.message.delete()

  # @reaction_role.command(name="title",hidden=True)
  # @commands.is_owner()
  # @commands.has_guild_permissions(manage_roles=True)
  # @commands.bot_has_guild_permissions(manage_roles=True)
  # async def reaction_title(self,ctx,*,title:str):
  #   self.msgs[ctx.channel.id]["title"] = title
  #   msg = await ctx.channel.fetch_message(self.msgs[ctx.channel.id]["id"])
  #   await asyncio.gather(
  #     ctx.message.delete(),
  #     msg.edit(embed=embed(title=title))
  #   )

  # @reaction_role.command(name="description",aliases=["desc"],hidden=True)
  # @commands.is_owner()
  # @commands.guild_only()
  # @commands.has_guild_permissions(manage_roles=True)
  # @commands.bot_has_guild_permissions(manage_roles=True)
  # async def reaction_description(self,ctx,*,description:str):
  #   self.msgs[ctx.channel.id]["description"] = title
  #   msg = await ctx.channel.fetch_message(self.msgs[ctx.channel.id]["id"])
  #   await asyncio.gather(
  #     ctx.message.delete(),
  #     msg.edit(embed=embed(description=description))
  #   )

  @commands.command(name="reactionrole", aliases=["rr"], hidden=True)
  @commands.is_owner()
  @commands.has_guild_permissions(manage_roles=True)
  @commands.bot_has_guild_permissions(manage_roles=True)
  @commands.bot_has_permissions(manage_messages=True)
  async def reaction_role(self, ctx, message: discord.Message, *, reaction_roles: str):
    reaction_roles = reaction_roles.split(" ")
    x = 0
    roles = {}
    for item in reaction_roles:
      item = item.split(";;")
      item[1] = "".join(item[1].split("<@&"))
      item[1] = "".join(item[1].split(">"))
      # print(item)
      role = await commands.RoleConverter().convert(ctx, item[1])
      # print(role)
      # item[1] = role.id
      roles.update({item[0]: role.id})
      # reaction_roles[x] = [item[0],ctx.guild.get_role(int(item[1]))]
      x = x + 1
    reaction_roles = roles
    print(reaction_roles)

    for emoji in reaction_roles:
      # emoji = emoji[0]
      print(emoji)
      await message.add_reaction(f"{emoji}")

    msg = None
    await ctx.reply(embed=embed(title=f"{message.jump_url} is a new reaction role message"))

    await asyncio.gather(
        ctx.message.delete(delay=self.bot.get_guild_delete_commands(ctx.guild)),
        msg.delete(delay=self.bot.get_guild_delete_commands(ctx.guild))
    )

    print({f"{message.jump_url}": {**reaction_roles}})

  # {message_id:{"🔗":role_id,"😈":role_id}}

  # Vote message


def setup(bot):
  bot.add_cog(ReactionRole(bot))
