from __future__ import annotations
# import asyncio

import discord
from discord.ext import commands

# from cogs.cleanup import get_delete_time
from functions import embed  # , checks
from typing import TYPE_CHECKING
# from interactions import Context as SlashContext, cog_ext, ComponentContext
# from discord_slash.model import SlashCommandOptionType
# from discord_slash.utils.manage_commands import create_option, create_choice
# from discord_slash.utils.manage_components import create_select, create_select_option, create_button, create_actionrow, wait_for_component, ButtonStyle
from functions import MyContext

if TYPE_CHECKING:
  from index import Friday as Bot


class AutoRole(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.bot = bot
    self.messages = {}
    # self.cancel_button = create_actionrow(create_button(ButtonStyle.red, "Cancel", custom_id="automod_cancel"))

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  def cog_check(self, ctx):
    if ctx.guild is None:
      raise commands.NoPrivateMessage("This command can only be used within a guild")
    return True

  # def component_check(self, payload: ComponentContext) -> bool:
  #   if payload.author_id not in {self.bot.owner_id, payload.origin_message.author.id, *self.bot.owner_ids}:
  #     return False
  #   return True

  @commands.command(name="autorole", hidden=True)
  @commands.is_owner()
  async def autorole(self, ctx: "MyContext"):
    ...

  # @cog_ext.cog_slash(name="autorole", description="Make an autorole", guild_ids=[243159711237537802])
  # @checks.slash(user=True, private=False)
  # async def slash_autorole(self, ctx: SlashContext):
  #   options = []
  #   for role in ctx.guild.roles:
  #     if role.name != "@everyone" and role.position < ctx.guild.me.top_role.position:
  #       options.append(create_select_option(role.name, value=str(role.id)))
  #   roles = create_select(
  #       options=[*options] if len(options) > 0 else [create_select_option("I lack perms for any role", "_", default=True)],
  #       custom_id="automod_roles_select",
  #       min_values=1,
  #       max_values=25 if len(options) > 25 else len(options) if len(options) > 0 else 1,
  #       disabled=False if len(options) > 0 else True,
  #   )
  #   message = await ctx.send("Choose the roles that you would like to add", components=[create_actionrow(roles), self.cancel_button], allowed_mentions=discord.AllowedMentions.none())
  #   self.messages.update({message.id: {}})

  # def yes_no_buttons(self, section: str) -> list:
  #   return [
  #       create_button(ButtonStyle.green, "Yes", custom_id=f"automod_{section}_q_yes", emoji="✅"),
  #       create_button(ButtonStyle.blue, "No", custom_id=f"automod_{section}_q_no", emoji="❌")
  #   ]

  # @commands.Cog.listener()
  # async def on_component(self, ctx: ComponentContext):
  #   check = self.component_check(ctx)
  #   if ctx.custom_id == "automod_cancel" and check:
  #     try:
  #       self.messages.pop(ctx.origin_message_id)
  #     except Exception:
  #       pass
  #     return await ctx.origin_message.delete()
  #   elif ctx.custom_id == "automod_roles_select" and check:
  #     await ctx.defer(edit_origin=True)
  #     self.messages[ctx.origin_message_id].update({"roles": ctx.selected_options, "embeded": None})
  #     await ctx.edit_origin(content=f"Roles: <@&{'>, <@&'.join(ctx.selected_options)}>\n\nWould you like this message to be embeded?", components=[create_actionrow(*self.yes_no_buttons("embed")), self.cancel_button], allowed_mentions=discord.AllowedMentions.none())
  #   elif ctx.custom_id == "automod_embed_q_no" and check:
  #     await ctx.defer(edit_origin=True)
  #     self.messages[ctx.origin_message_id].update({"embeded": False, "colors": None})
  #     await ctx.edit_origin(content=f"Roles: <@&{'>, <@&'.join(self.messages[ctx.origin_message_id]['roles'])}>\nEmbed: {self.messages[ctx.origin_message_id]['embeded']}\n\nWould you like to setup button colors?", components=[create_actionrow(*self.yes_no_buttons("colors")), self.cancel_button])
  #   elif ctx.custom_id == "automod_embed_q_yes" and check:
  #     await ctx.defer(edit_origin=True)
  #     self.messages[ctx.origin_message_id].update({"embeded": True, "title": None, "description": None})
  #     await ctx.edit_origin(content=f"Roles: <@&{'>, <@&'.join(self.messages[ctx.origin_message_id]['roles'])}>\nEmbed: {self.messages[ctx.origin_message_id]['embeded']}\n\n**Reply** to this message with the title of the embed you would like to display", components=[self.cancel_button])
  #   elif ctx.custom_id == "automod_colors_q_no" and check:
  #     self.messages[ctx.origin_message_id].update({"embeded": False, "content": None})
  #     await ctx.edit_origin(content=f"Roles: <@&{'>, <@&'.join(self.messages[ctx.origin_message_id]['roles'])}>\nEmbed: {self.messages[ctx.origin_message_id]['embeded']}\nColors: Default\n\nWould you like to setup emojis?", components=[create_actionrow(*self.yes_no_buttons("emojis")), self.cancel_button])
  #   elif ctx.custom_id == "automod_colors_q_yes" and check:
  #     self.messages[ctx.origin_message_id].update({"embeded": False, "content": None})
  #     await ctx.edit_origin(content=f"Roles: <@&{'>, <@&'.join(self.messages[ctx.origin_message_id]['roles'])}>\nEmbed: {self.messages[ctx.origin_message_id]['embeded']}\n\n**Reply** to this message with the message that you would like to display", components=[self.cancel_button])
  #   elif ctx.custom_id == "automod_emojis_q_no" and check:
  #     self.messages[ctx.origin_message_id].update({"embeded": False, "content": None})
  #     await ctx.edit_origin(content=f"Roles: <@&{'>, <@&'.join(self.messages[ctx.origin_message_id]['roles'])}>\nEmbed: {self.messages[ctx.origin_message_id]['embeded']}\nColors: Default\n\nWould you like to setup emojis?", components=[create_actionrow(*self.yes_no_buttons("emojis")), self.cancel_button])
  #   elif ctx.custom_id == "automod_emojis_q_yes" and check:
  #     self.messages[ctx.origin_message_id].update({"embeded": False, "content": None})
  #     await ctx.edit_origin(content=f"Roles: <@&{'>, <@&'.join(self.messages[ctx.origin_message_id]['roles'])}>\nEmbed: {self.messages[ctx.origin_message_id]['embeded']}\n\n**Reply** to this message with the message that you would like to display", components=[self.cancel_button])
  #   elif ctx.custom_id.startswith("automod_roles_"):
  #     await ctx.defer(hidden=True)
  #     role = ctx.guild.get_role(int("".join(ctx.custom_id.split("automod_roles_"))))
  #     if role.id not in [r.id for r in ctx.author.roles]:
  #       await ctx.author.add_roles(role, reason="Auto roles", atomic=True)
  #       await ctx.send(content=f"Applied role {role.mention}", hidden=True)
  #     else:
  #       await ctx.author.remove_roles(role, reason="Auto roles", atomic=True)
  #       await ctx.send(content=f"Removed role {role.mention}", hidden=True)

  # @commands.Cog.listener()
  # async def on_message(self, msg: discord.Message):
  #   if msg.author.bot or msg.type.name != "reply" or not msg.reference:
  #     return
  #   content = msg.clean_content
  #   if msg.reference.cached_message is not None and isinstance(msg.reference.cached_message, discord.Message):
  #     message = msg.reference.cached_message
  #     if message.author.id != self.bot.user.id or message.id not in self.messages:
  #       return
  #     await msg.delete()
  #     if self.messages[message.id]["embeded"] is True and self.messages[message.id]["title"] is None:
  #       self.messages[message.id]["title"] = content
  #       await message.edit(content=f"Roles: <@&{'>, <@&'.join(self.messages[message.id]['roles'])}>\nEmbed: {self.messages[message.id]['embeded']}\nTitle:```{self.messages[message.id]['title']}```\n\n**Reply** to this message with the description you would like to display")
  #     elif self.messages[message.id]["embeded"] is True and self.messages[message.id]["description"] is None:
  #       self.messages[message.id]["description"] = content
  #       components, message = [], self.messages.pop(message.id)
  #       for role in [r for r in await msg.guild.fetch_roles() if r.id in [int(i) for i in message["roles"]]]:
  #         components.append(create_button(style=ButtonStyle.blurple, label=role.name, custom_id=f"automod_roles_{role.id}"))
  #       await msg.channel.send(embed=embed(title=message["title"], description=message["description"]), components=[create_actionrow(*components)])
  #       await msg.reference.cached_message.delete()
  #       # await message.edit(content=f"Roles: <@&{'>, <@&'.join(self.messages[message.id]['roles'])}>\nEmbed: {self.messages[message.id]['embeded']}\nTitle:```{self.messages[message.id]['title']}```Description:```{self.messages[message.id]['description']}```\n\n")
  #     elif self.messages[message.id]["embeded"] is False and self.messages[message.id]["content"] is None:
  #       self.messages[message.id]["content"] = content
  #       components, message = [], self.messages[message.id]
  #       last, roles = 0.0, [r for r in await msg.guild.fetch_roles() if r.id in [int(i) for i in message["roles"]]]
  #       rows, _ = divmod(len(roles), 5)
  #       avg = len(roles) / (float(rows) if rows > 0 else 1.0)
  #       roles = [create_button(style=ButtonStyle.blue, label=role.name, custom_id=f"automod_roles_{role.id}") for role in roles]
  #       while last < len(roles):
  #         components.append(reversed(roles[int(last):int(last + avg)]))
  #         last += avg
  #       new = components
  #       components = []
  #       for item in reversed(new):
  #         fuck = [i for i in item]
  #         nigger = create_actionrow(*fuck)
  #         components.append(nigger)
  #       # for role in roles:
  #       #   # row, _ = divmod(x, 5)
  #       #   if last < len(roles):
  #       #     # components.append(roles[create_button(style=ButtonStyle.blurple, label=role.name, custom_id=f"automod_roles_{role.id}"):])
  #       #     components.append(roles[role.id * -1:role.id])
  #       #     last += avg

  #         # x += 1
  #       await msg.channel.send(content=message["content"], components=[*components])
  #       await msg.reference.cached_message.delete()
  #       # await message.edit(content=f"Roles: <@&{'>, <@&'.join(self.messages[message.id]['roles'])}>\nEmbed: {self.messages[message.id]['embeded']}\nContent:```{self.messages[message.id]['content']}```\n\n")

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
  @commands.bot_has_permissions(manage_messages=True, add_reactions=True)
  async def reaction_role(self, ctx, message: discord.Message, *, reaction_roles: str):
    new_reaction_roles = reaction_roles.split(" ")
    x = 0
    roles = {}
    for item in new_reaction_roles:
      item = item.split(";;")
      item[1] = "".join(item[1].split("<@&"))
      item[1] = "".join(item[1].split(">"))
      # print(item)
      role = await commands.RoleConverter().convert(ctx, item[1])
      # print(role)
      # item[1] = role.id
      roles.update({item[0]: role.id})
      # new_reaction_roles[x] = [item[0],ctx.guild.get_role(int(item[1]))]
      x = x + 1
    new_reaction_roles = roles
    print(new_reaction_roles)

    for emoji in new_reaction_roles:
      # emoji = emoji[0]
      print(emoji)
      await message.add_reaction(f"{emoji}")

    # msg = None
    await ctx.reply(embed=embed(title=f"{message.jump_url} is a new reaction role message"))

    # await asyncio.gather(
    #     ctx.message.delete(delay=self.bot.log.get_guild_delete_commands(ctx.guild)),
    #     msg.delete(delay=self.bot.log.get_guild_delete_commands(ctx.guild))
    # )

    print({f"{message.jump_url}": {**new_reaction_roles}})

  # {message_id:{"🔗":role_id,"😈":role_id}}

  # Vote message


async def setup(bot):
  ...
  # bot.add_cog(AutoRole(bot))
