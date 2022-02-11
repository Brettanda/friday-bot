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


class FakeInteractionMessage:
  """Turns an `discord.Interaction` into sudo a `discord.Message`"""

  def __init__(self, bot: "Bot", interaction: discord.Interaction):
    self._bot = bot
    self.interaction = interaction
    super().__init__()

  @property
  def bot(self) -> Union["Bot", discord.Client, discord.AutoShardedClient]:
    return self._bot

  @property
  def channel(self) -> Union[discord.TextChannel, discord.DMChannel]:
    return self.interaction.channel

  @property
  def guild(self) -> discord.Guild:
    return self.interaction.guild

  @property
  def author(self) -> Union[discord.User, discord.Member]:
    return self.interaction.user

  @property
  def type(self) -> discord.MessageType:
    return discord.MessageType.application_command

  @property
  def content(self) -> str:
    options = [f"{i.get('name', 'no-name')} {i.get('value', 'no-value')}" for i in self.interaction.data.get("options", [])]
    return f"/{self.interaction.data['name']} {', '.join(options)}"

  async def add_reaction(self, *args, **kwargs) -> discord.Message.add_reaction:
    if self.interaction.message is None:
      self.interaction.message = await self.interaction.original_message()
    return await self.interaction.message.add_reaction(*args, **kwargs)

  @property
  def clean_content(self) -> str:
    options = [f"{i.get('name', 'no-name')} {i.get('value', 'no-value')}" for i in self.interaction.data.get("options", [])]
    return f"/{self.interaction.data['name']} {', '.join(options)}"

  async def delete(self, *args, **kwargs) -> None:
    """There should be no message to delete so just like ignore this function"""
    return None

  async def reply(self, content, **kwargs) -> discord.Message:
    kwargs.pop("delete_after", None)
    return await self.interaction.response.send_message(content, **kwargs)

  @property
  def _state(self) -> discord.Interaction._state:
    return self.interaction._state


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

  async def send(self, content: str = None, *, delete_original: bool = False, **kwargs) -> Optional[Union[discord.Message, FakeInteractionMessage]]:
    return await self.reply(content, delete_original=delete_original, **kwargs)

  async def safe_send(self, content: str, *, escape_mentions=True, **kwargs) -> Optional[Union[discord.Message, FakeInteractionMessage]]:
    if escape_mentions:
      content = discord.utils.escape_mentions(content)

    if len(content) > 2000:
      fp = io.BytesIO(content.encode())
      kwargs.pop("file", None)
      return await self.send(file=discord.File(fp, filename="message_too_long.txt"), **kwargs)
    else:
      return await self.send(content, **kwargs)
