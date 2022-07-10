# from __future__ import annotations

# import json
# from collections import defaultdict
# from typing import TYPE_CHECKING, List, Optional, Tuple

# import discord
# from discord.ext import commands
# from typing_extensions import Annotated

# from functions import embed

# if TYPE_CHECKING:
#   from functions.custom_contexts import GuildContext, MyContext
#   from index import Friday as Bot


# class EmbedsFlags(commands.FlagConverter, delimiter=' ', prefix="--", case_insensitive=True):
#   name: Optional[str]
#   title: Optional[str]
#   description: Optional[str] = commands.flag(name="description", aliases=["desc"])
#   url: Optional[str] = commands.flag(name="url", aliases=["link"])
#   colour: Optional[discord.Colour]
#   color: Optional[discord.Color] = commands.flag(default=discord.Colour.default())
#   footer: Optional[str]
#   footer_icon: Optional[str]
#   image: Optional[str]
#   thumbnail: Optional[str]
#   author_name: Optional[str]
#   author_icon: Optional[str]
#   fields: List[Tuple[str, str, bool]] = commands.flag(name="field", aliases=["opt", "option"], max_args=25, default=lambda ctx: [])
#   sendonly: bool = commands.flag(name="sendonly", aliases=["noedit"], default=False)


# class Embed(commands.Converter):
#   async def convert(self, ctx: MyContext, argument):
#     e = await EmbedsFlags.convert(ctx, argument)

#     if not e.title and not e.description and not e.image and len(e.fields) == 0 and not e.footer:
#       raise commands.BadArgument("Can't create an empty embed.")

#     if not e.name and not e.sendonly:
#       raise commands.BadArgument("You must provide a name or set sendonly to True.")

#     if e.title and len(e.title) > 256:
#       raise commands.BadArgument("Title cannot be longer than 256 characters.")

#     if e.description and len(e.description) > 4096:
#       raise commands.BadArgument("Description cannot be longer than 4096 characters.")

#     def is_url(url: str) -> bool:
#       return bool(url and url.startswith("http://") or url.startswith("https://") and len(url.split(" ")) == 1)

#     if e.url and not is_url(e.url):
#       raise commands.BadArgument("URL must be a valid URL. must start with http:// or https://")

#     if e.footer_icon and not is_url(e.footer_icon):
#       raise commands.BadArgument("Footer icon must be a valid URL. must start with http:// or https://")

#     if e.author_icon and not is_url(e.author_icon):
#       raise commands.BadArgument("Author icon must be a valid URL. must start with http:// or https://")

#     if e.image and not is_url(e.image):
#       raise commands.BadArgument("Image must be a valid URL. must start with http:// or https://")

#     if e.thumbnail and not is_url(e.thumbnail):
#       raise commands.BadArgument("Thumbnail must be a valid URL. must start with http:// or https://")

#     for field in e.fields:
#       if len(field[0]) > 256:
#         raise commands.BadArgument("Field title cannot be longer than 256 characters.")

#       if len(field[1]) > 1024:
#         raise commands.BadArgument("Field description/value cannot be longer than 1024 characters.")

#     # if len(e) > 6000:
#     #   raise commands.BadArgument("Embed cannot be longer than 6000 characters.")

#     return e


# # class EmbedToggler(discord.ui.Select):
# #   def __init__(self):
# #     super().__init__(custom_id="embedcreator_toggler", placeholder="Select something", max_values=len(options), options=options)

# #   async def callback(self, interaction: discord.Interaction):
# #     ...


# class EmbedMaker(discord.ui.View):
#   options: List[discord.SelectOption] = [
#       discord.SelectOption(label="Title", value="title", default=True),
#       discord.SelectOption(label="Description", value="description"),
#       discord.SelectOption(label="URL", value="url"),
#       discord.SelectOption(label="Colour", value="color"),
#       discord.SelectOption(label="Footer", value="footer_text"),
#       discord.SelectOption(label="Footer icon", value="footer_icon_url"),
#       discord.SelectOption(label="Image", value="image_url"),
#       discord.SelectOption(label="Thumbnail", value="thumbnail"),
#       discord.SelectOption(label="Author name", value="author_name"),
#       discord.SelectOption(label="Author icon", value="author_icon_url"),
#       discord.SelectOption(label="Fields", value="fields"),
#   ]

#   def __init__(self, *, author_id: int = None):
#     self.author_id = author_id
#     super().__init__(timeout=None)
#     self.defaults = {
#         "title": "Title",
#         "description": "Description",
#         "url": "https://example.com",
#         "color": discord.Color.green().value,
#         "footer": {
#             "text": "Footer",
#             "icon_url": "https://picsum.photos/seed/friday/120/120",
#         },
#         "image": {
#             "url": "https://picsum.photos/seed/friday/400/200",
#         },
#         "thumbnail": {
#             "url": "https://picsum.photos/seed/friday/200/200",
#         },
#         "author": {
#             "name": "Author",
#             "icon_url": "https://picsum.photos/seed/friday/120/120",
#         },
#         "fields": {
#             "name": "Field Title",
#             "value": "Field Description",
#             "inline": True,
#         }
#     }
#     self.current_embed = defaultdict(lambda: None)
#     self.field_count.value = 1
#     self.remove_item(self.field_count)

#   async def interaction_check(self, interaction: discord.Interaction) -> bool:
#     if not self.author_id and interaction.message.reference:
#       ref = await interaction.channel.fetch_message(interaction.message.reference.message_id)
#       self.author_id = ref.author.id
#     if interaction.user and interaction.user.id == self.author_id:
#       return True
#     else:
#       await interaction.response.send_message('This confirmation dialog is not for you.', ephemeral=True)
#       return False

#   @discord.ui.select(custom_id="embedcreator_toggler", placeholder="Select something", options=options, max_values=len(options))
#   async def toggler(self, interaction: discord.Interaction, select: discord.ui.Select):
#     old_e = interaction.message.embeds[0]
#     self.current_embed.update(old_e.to_dict())
#     new_e = defaultdict(lambda: None)

#     self.clear_items()
#     self.add_item(self.toggler)

#     for v in select.values:
#       vs = v.split("_")
#       l = "_".join(vs[1:])
#       if v == "fields":
#         new_e.update({v: []})
#         if len(self.current_embed[v]) > 1 and "fields" in self.current_embed[v]:
#           for f in self.current_embed[v]["fields"]:
#             new_e[v].append(f.copy())
#         else:
#           for n in range(0, int(self.field_count.value)):
#             new_e[v].append(self.defaults[v].copy())
#         if self.field_count not in self.children:
#           self.add_item(self.field_count)
#       elif len(vs) > 1 and vs[0] in self.defaults.keys() and not vs[0] in new_e.keys():
#         new_e.update({
#             vs[0]: {
#                 l: len(self.current_embed[vs[0]]) > 1 and self.current_embed[vs[0]][l] or self.defaults[vs[0]][l]
#             }
#         })
#       elif len(vs) > 1 and vs[0] in new_e.keys():
#         new_e[vs[0]][l] = len(self.current_embed[vs[0]]) > 1 and self.current_embed[vs[0]][l] or self.defaults[vs[0]][l]
#       elif v in self.defaults:
#         new_e.update({v: self.current_embed[v] or self.defaults[v]})

#     new_e = discord.Embed.from_dict(dict(new_e))

#     for o in select.options:
#       o.default = False
#       for v in select.values:
#         if o.value == v:
#           o.default = True
#           break

#     # for o in self.field_count.options:
#     #   o.default = False
#     #   for v in self.field_count.values:
#     #     if str(o.value) == v:
#     #       o.default = True
#     #       break

#     self.field_count.disabled = "fields" not in select.values

#     await interaction.response.edit_message(embed=new_e, view=self)

#   @discord.ui.select(custom_id="embedcreator_field_count", disabled=True, options=[discord.SelectOption(label=n, default=n == 1) for n in range(1, 26)])
#   async def field_count(self, interaction: discord.Interaction, select: discord.ui.Select):
#     old_e = interaction.message.embeds[0]
#     self.current_embed.update(old_e.to_dict())

#     self.field_count.value = select.values[0]

#     new_e = old_e.copy()
#     new_e.clear_fields()

#     for n in range(0, int(select.values[0])):
#       if n < len(new_e.fields):
#         new_e.set_field_at(
#             n,
#             name=self.current_embed["fields"][n]["name"] or self.defaults["fields"]["name"],
#             value=self.current_embed["fields"][n]["value"] or self.defaults["fields"]["value"],
#             inline=self.current_embed["fields"][n]["inline"] or self.defaults["fields"]["inline"]
#         )
#       else:
#         new_e.add_field(
#             name=self.defaults["fields"]["name"],
#             value=self.defaults["fields"]["value"],
#             inline=self.defaults["fields"]["inline"],
#         )

#     for o in select.options:
#       o.default = False
#       for v in select.values:
#         if str(o.value) == v:
#           o.default = True
#           break

#     for o in self.toggler.options:
#       o.default = False
#       for v in self.toggler.values:
#         if o.value == v:
#           o.default = True
#           break

#     await interaction.response.edit_message(embed=new_e, view=self)


# class Embeds(commands.Cog):
#   def __init__(self, bot: "Bot"):
#     self.bot = bot

#   def __repr__(self) -> str:
#     return f"<cogs.{self.__cog_name__}>"

#   @commands.Cog.listener()
#   async def on_ready(self):
#     if not self.bot.views_loaded:
#       self.bot.add_view(EmbedMaker())

#   @commands.group("embedder", aliases=["embed"], invoke_without_command=True, case_insensitive=True)
#   @commands.guild_only()
#   async def embedder(self, ctx: GuildContext, channel: Optional[discord.TextChannel] = None, *, options: Annotated[discord.Embed, Embed]):
#     text_channel = channel or ctx.channel

#     # if options.sendonly:
#     #   confirm = await ctx.prompt("This embed will be sent without saving. Do you want to continue?")
#     #   if not confirm:
#     #     return await ctx.send(embed=embed(title="Cancelled.", colour=MessageColors.error()))
#     # else:
#     if not options.sendonly:
#       record_count = await ctx.db.fetchval("SELECT COUNT(*) FROM embeds WHERE guild_id=$1", text_channel.guild.id)
#       if record_count > 5:
#         raise commands.BadArgument("You can't have more than 5 embeds in a server.")

#     e = embed(
#         title=options.title,
#         description=options.description,
#         url=options.url,
#         colour=options.colour or options.color,
#         footer=options.footer,
#         footer_icon=options.footer_icon,
#         image=options.image,
#         thumbnail=options.thumbnail,
#         author_name=options.author_name,
#         author_icon=options.author_icon,
#         fieldstitle=[f[0] for f in options.fields],
#         fieldsval=[f[1] for f in options.fields],
#         fieldsin=[f[2] for f in options.fields],
#     )
#     msg = await text_channel.send(embed=e)

#     if not options.sendonly:
#       query = """INSERT INTO embeds (guild_id, channel_id, message_id, embed) VALUES ($1, $2, $3, $4::JSONB)"""
#       await ctx.db.execute(query, ctx.guild.id, text_channel.id, msg.id, json.dumps(e.to_dict()))

#   @embedder.command("edit")
#   async def embedder_edit(self, ctx: MyContext, message: discord.Message, *, options: Embed):
#     ...

#   @embedder.command("new")
#   async def embedder_new(self, ctx: MyContext):
#     await ctx.send(embed=discord.Embed(title="Title"), view=EmbedMaker(author_id=ctx.author.id))

#   @embedder.command("delete")
#   async def embedder_delete(self, ctx: MyContext, message: discord.Message):
#     ...

#   @embedder.command("list")
#   async def embedder_list(self, ctx: MyContext):
#     query = """SELECT channel_id, message_id FROM embeds WHERE guild_id=$1"""
#     embeds = await ctx.db.fetch(query, ctx.guild.id)

#     await ctx.send(f"{len(embeds)} embeds in this server.")


async def setup(bot):
  ...
  # await bot.add_cog(Embeds(bot))
