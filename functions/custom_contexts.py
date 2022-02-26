from __future__ import annotations
# from interactions import Context as SlashContext
from discord.ext.commands import Context
import discord
import io
from typing import Optional, Union
from typing_extensions import TYPE_CHECKING

from .myembed import embed

if TYPE_CHECKING:
  from index import Friday as Bot
  from cogs.database import Database
  from aiohttp import ClientSession
  from asyncpg import Pool


# class MySlashContext(SlashContext):
#   def __init__(self):
#     self.reply = self.reply

#   async def reply(self, content=None, **kwargs):
#     await self.send(content, **kwargs)
#     # if not hasattr(kwargs,"delete_after") and self.command.name not in ["meme","issue","reactionrole","minesweeper"]:
#     #   delete = await get_delete_time(self)
#     #   delete = delete if delete is not None and delete != 0 else None
#     #   if delete != None:
#     #     kwargs.update({"delete_after":delete})
#     #     await self.message.delete(delay=delete)
#     # try:
#     #   return await self.message.reply(content,**kwargs)
#     # except discord.Forbidden as e:
#     #   if "Cannot reply without permission" in str(e):
#     #     return await self.message.channel.send(content,**kwargs)
#     #   else:
#     #     raise e
#     # except discord.HTTPException as e:
#     #   if "Unknown message" in str(e):
#     #     return await self.message.channel.send(content,**kwargs)
#     #   else:
#     #     raise e


class ConfirmationView(discord.ui.View):
  def __init__(self, *, timeout: float, author_id: int, ctx: Context) -> None:
    super().__init__(timeout=timeout)
    self.value: Optional[bool] = None
    self.author_id: int = author_id
    self.ctx: Context = ctx
    self.message: Optional[discord.Message] = None

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if interaction.user and interaction.user.id == self.author_id:
      return True
    else:
      await interaction.response.send_message('This confirmation dialog is not for you.', ephemeral=True)
      return False

  async def on_timeout(self) -> None:
    try:
      await self.message.delete()
    except discord.NotFound:
      pass

  @discord.ui.button(emoji="\N{HEAVY CHECK MARK}", label='Confirm', custom_id="confirmation_true", style=discord.ButtonStyle.green)
  async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
    self.value = True
    await interaction.response.defer()
    await interaction.delete_original_message()
    self.stop()

  @discord.ui.button(emoji="\N{HEAVY MULTIPLICATION X}", label='Cancel', custom_id="confirmation_false", style=discord.ButtonStyle.red)
  async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
    self.value = False
    await interaction.response.defer()
    await interaction.delete_original_message()
    self.stop()


class MultiSelectView(discord.ui.View):
  def __init__(self, options: list, *, values: list = [], emojis: list = [], descriptions: list = [], placeholder: str = None, min_values: int = 1, max_values: int = 1, default: str = None, timeout: float, author_id: int, ctx: Context) -> None:
    super().__init__(timeout=timeout)
    values = values if len(values) > 0 else [None] * len(options)
    emojis = emojis if len(emojis) > 0 else [None] * len(options)
    descriptions = descriptions if len(descriptions) > 0 else [None] * len(options)
    self.options: list = [discord.SelectOption(label=p, value=v, emoji=e, description=d, default=True if default == v else False) for p, v, e, d in zip(options, values, emojis, descriptions)]
    self.placeholder: Optional[str] = placeholder
    self.author_id: int = author_id
    self.ctx: Context = ctx
    self.min_values: int = min_values
    self.max_values: int = max_values
    self.message: Optional[discord.Message] = None

    self.values: Optional[list] = None

    self.select.options = self.options
    self.select.placeholder = self.placeholder
    self.select.min_values = self.min_values
    self.select.max_values = self.max_values

  @discord.ui.select(custom_id="prompt_select", options=["Loading..."], min_values=0, max_values=0)
  async def select(self, select: discord.ui.Select, interaction: discord.Interaction):
    self.values = select.values
    await interaction.response.defer()
    await interaction.delete_original_message()
    self.stop()

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if interaction.user and interaction.user.id == self.author_id:
      return True
    else:
      await interaction.response.send_message('This confirmation dialog is not for you.', ephemeral=True)
      return False

  async def on_timeout(self) -> None:
    try:
      await self.message.delete()
    except discord.NotFound:
      pass


# class Modal(discord.ui.Modal):
#   def __init__(self, title: str, items: List[dict]):
#     super().__init__(title)
#     self.values: Optional[list] = None
#     for item in items:
#       self.add_item(discord.ui.InputText(**item))

#   async def callback(self, interaction: discord.Interaction):
#     await interaction.response.defer()
#     return [c.value for c in self.children]
#     # embed = discord.Embed(title="Your Modal Results", color=discord.Color.random())
#     # embed.add_field(name="First Input", value=self.children[0].value, inline=False)
#     # # embed.add_field(name="Second Input", value=self.children[1].value, inline=False)
#     # await interaction.response.send_message(embeds=[embed])


# class ModalView(discord.ui.View):
#   def __init__(self, *, modal_button: Optional[str] = "Modal", modal_title: Optional[str] = "Modal", modal_items: List[dict] = [], author_id: int):
#     super().__init__(timeout=60.0)
#     self._modal_button: Optional[str] = modal_button
#     self._modal_title: Optional[str] = modal_title
#     self._modal_items: List[dict] = modal_items
#     self.author_id: int = author_id

#     self.button_modal.label = modal_button

#   async def interaction_check(self, interaction: discord.Interaction) -> bool:
#     if interaction.user and interaction.user.id == self.author_id:
#       return True
#     else:
#       await interaction.response.send_message('This confirmation dialog is not for you.', ephemeral=True)
#       return False

#   @discord.ui.button(label="Modal", style=discord.ButtonStyle.primary)
#   async def button_modal(self, button, interaction: discord.Interaction):
#     await interaction.response.send_modal(Modal(
#         title=self._modal_title,
#         items=self._modal_items
#     ))
#     self.stop()

#   async def on_timeout(self) -> None:
#     try:
#       await self.message.delete()
#     except discord.NotFound:
#       pass


class MyContext(Context):
  def __init__(self, *args, **kwargs):
    self.to_bot_channel: int = None
    super().__init__(*args, **kwargs)

  def __repr__(self) -> str:
    return "<Context>"

  @discord.utils.cached_property
  def replied_reference(self) -> Optional[discord.MessageReference]:
    ref = self.message.reference
    if ref and isinstance(ref.resolved, discord.Message):
      return ref.resolved.to_reference()
    return None

  @property
  def session(self) -> ClientSession():
    return self.bot.session

  @property
  def db(self) -> Database:
    return self.bot.db

  @property
  def pool(self) -> Pool:
    return self.bot.db.pool

  async def prompt(self, message: str, *, timeout: float = 60.0, author_id: Optional[int] = None, **kwargs) -> Optional[bool]:
    author_id = author_id or self.author.id
    view = ConfirmationView(
        timeout=timeout,
        ctx=self,
        author_id=author_id
    )
    kwargs["embed"] = kwargs.pop("embed", embed(title=message))
    view.message = await self.send(view=view, **kwargs)
    await view.wait()
    return view.value

  async def multi_select(self, message: str = "Please select one or more of the options.", options: list = [], *, values: list = [], emojis: list = [], descriptions: list = [], default: str = None, placeholder: str = None, min_values: int = 1, max_values: int = 1, timeout: float = 60.0, author_id: Optional[int] = None, **kwargs) -> Optional[list]:
    author_id = author_id or self.author.id
    view = MultiSelectView(
        options=options,
        values=values,
        emojis=emojis,
        descriptions=descriptions,
        default=default,
        placeholder=placeholder,
        timeout=timeout,
        min_values=min_values,
        max_values=max_values,
        ctx=self,
        author_id=author_id,
    )
    kwargs["embed"] = kwargs.pop("embed", embed(title=message))
    view.message = await self.send(view=view, **kwargs)
    await view.wait()
    return view.values

  # async def modal(self, message: str, *, modal_button: Optional[str] = "Modal", modal_title: Optional[str] = "Modal", modal_items: List[dict] = [], author_id: Optional[int] = None, **kwargs):
  #   author_id = author_id or self.author.id
  #   view = ModalView(
  #       modal_button=modal_button,
  #       modal_title=modal_title,
  #       modal_items=modal_items,
  #       author_id=author_id,
  #   )
  #   kwargs["embed"] = kwargs.pop("embed", embed(title=message))
  #   view.message = await self.send(view=view, **kwargs)
  #   await view.wait()
  #   return view.value

  async def reply(self, content: str = None, *, delete_original: bool = False, reply_to_replied: bool = True, **kwargs) -> Optional[discord.Message]:
    message = None
    if not hasattr(kwargs, "mention_author") and self.message.type.name != "application_command":
      kwargs.update({"mention_author": False})
    if self.to_bot_channel is not None:
      content = f"{self.author.mention}\n{content if content else ''}"
      try:
        channel = self.bot.get_channel(self.to_bot_channel)
        if channel is None:
          channel = await self.bot.fetch_channel(self.to_bot_channel)
          if channel is None:
            # Bruh
            return
        message = await channel.send(content, **kwargs)
      except (discord.Forbidden, discord.HTTPException):
        return message
      return message
    try:
      if self.message.type == discord.MessageType.thread_starter_message:
        message = await self.message.channel.send(content, **kwargs)
      message = await self.message.channel.send(content, reference=self.replied_reference or self.message, **kwargs)
    except (discord.Forbidden, discord.HTTPException):
      try:
        message = await self.message.channel.send(content, **kwargs)
      except (discord.Forbidden, discord.HTTPException):
        return message
    return message

  async def send(self, content: str = None, *, delete_original: bool = False, **kwargs) -> Optional[discord.Message]:
    return await self.reply(content, delete_original=delete_original, **kwargs)

  async def safe_send(self, content: str, *, escape_mentions=True, **kwargs) -> Optional[discord.Message]:
    if escape_mentions:
      content = discord.utils.escape_mentions(content)

    if len(content) > 2000:
      fp = io.BytesIO(content.encode())
      kwargs.pop("file", None)
      return await self.send(file=discord.File(fp, filename="message_too_long.txt"), **kwargs)
    else:
      return await self.send(content, **kwargs)
