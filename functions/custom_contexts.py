from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any, Protocol, List, Optional, Union

import discord
from discord.ext import commands

from .myembed import embed

if TYPE_CHECKING:
  from aiohttp import ClientSession
  from asyncpg import Connection, Pool

  from index import Friday
  from types import TracebackType


class ConnectionContextManager(Protocol):
  async def __aenter__(self) -> Connection:
    ...

  async def __aexit__(
      self,
      exc_type: Optional[type[BaseException]],
      exc_value: Optional[BaseException],
      traceback: Optional[TracebackType]
  ) -> None:
    ...


class DatabaseProtocol(Protocol):
  async def execute(self, query: str, *args: Any, timeout: Optional[float] = None) -> str:
    ...

  async def fetch(self, query: str, *args: Any, timeout: Optional[float] = None) -> list[Any]:
    ...

  async def fetchrow(self, query: str, *args: Any, timeout: Optional[float] = None) -> Optional[Any]:
    ...

  async def fetchval(self, query: str, *args: Any, timeout: Optional[float] = None) -> Optional[Any]:
    ...

  def acquire(self, *, timeout: Optional[float] = None) -> ConnectionContextManager:
    ...

  def release(self, connection: Connection) -> None:
    ...


class ConfirmationView(discord.ui.View):
  def __init__(self, *, timeout: float, author_id: int, ctx: MyContext, delete_after: bool) -> None:
    super().__init__(timeout=timeout)
    self.value: Optional[bool] = None
    self.delete_after: bool = delete_after
    self.author_id: int = author_id
    self.ctx: MyContext = ctx
    self.message: Optional[discord.Message] = None

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if interaction.user and interaction.user.id == self.author_id:
      return True
    else:
      await interaction.response.send_message('This confirmation dialog is not for you.', ephemeral=True)
      return False

  async def on_timeout(self) -> None:
    if self.delete_after and self.message:
      await self.message.delete()

  @discord.ui.button(emoji="\N{HEAVY CHECK MARK}", label='Confirm', custom_id="confirmation_true", style=discord.ButtonStyle.green)
  async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
    self.value = True
    await interaction.response.defer()
    if self.delete_after:
      await interaction.delete_original_response()
    self.stop()

  @discord.ui.button(emoji="\N{HEAVY MULTIPLICATION X}", label='Cancel', custom_id="confirmation_false", style=discord.ButtonStyle.red)
  async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
    self.value = False
    await interaction.response.defer()
    if self.delete_after:
      await interaction.delete_original_response()
    self.stop()


class MultiSelectView(discord.ui.View):
  def __init__(self, options: list, *, values: list = [], emojis: list = [], descriptions: list = [], placeholder: str = None, min_values: int = 1, max_values: int = 1, default: str = None, timeout: float, delete_after: bool, author_id: int, ctx: MyContext) -> None:
    super().__init__(timeout=timeout)
    new = False
    if not values and not emojis and not descriptions:
      new = True
    values = values if len(values) > 0 else [None] * len(options)
    emojis = emojis if len(emojis) > 0 else [None] * len(options)
    descriptions = descriptions if len(descriptions) > 0 else [None] * len(options)
    if not new:
      self.options: list = [discord.SelectOption(label=p, value=v or p, emoji=e, description=d, default=True if default == v else False) for p, v, e, d in zip(options, values, emojis, descriptions)]
    else:
      self.options = [discord.SelectOption(**ks) for ks in options]
    self.placeholder: Optional[str] = placeholder
    self.author_id: int = author_id
    self.ctx: MyContext = ctx
    self.min_values: int = min_values
    self.max_values: int = max_values
    self.delete_after: bool = delete_after
    self.message: Optional[discord.Message] = None

    self.values: Optional[list] = None

    self.select.options = self.options
    self.select.placeholder = self.placeholder
    self.select.min_values = self.min_values
    self.select.max_values = self.max_values

  @discord.ui.select(custom_id="prompt_select", options=[discord.SelectOption(label="Loading...")], min_values=0, max_values=0)
  async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
    self.values = select.values
    await interaction.response.defer()
    if self.delete_after:
      await interaction.delete_original_response()
    self.stop()

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if interaction.user and interaction.user.id == self.author_id:
      return True
    else:
      await interaction.response.send_message('This confirmation dialog is not for you.', ephemeral=True)
      return False

  async def on_timeout(self) -> None:
    if self.delete_after and self.message:
      await self.message.delete()


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
class MyContext(commands.Context):
  channel: Union[discord.VoiceChannel, discord.TextChannel, discord.Thread, discord.DMChannel]
  prefix: str
  command: commands.Command[Any, ..., Any]
  bot: Friday

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.pool: Pool = self.bot.pool
    self._bot_message: Optional[discord.Message] = None

  def __repr__(self) -> str:
    return "<Context>"

  @discord.utils.cached_property
  def replied_reference(self) -> Optional[discord.MessageReference]:
    ref = self.message.reference
    if ref and isinstance(ref.resolved, discord.Message):
      return ref.resolved.to_reference()
    return None

  @property
  def session(self) -> ClientSession:
    return self.bot.session

  @property
  def bot_message(self) -> Optional[discord.Message]:
    return self._bot_message

  @property
  def db(self) -> DatabaseProtocol:
    return self.pool

  @property
  def lang_code_user(self) -> str:
    if self.interaction:
      return self.interaction.locale.value.split("-")[0]
    return self.bot.languages.get(self.author.id, "en")

  @property
  def lang_code(self) -> str:
    if self.interaction:
      return self.interaction.locale.value.split("-")[0]
    guild = self.guild and self.bot.languages.get(self.guild.id, None)
    return guild or self.lang_code_user

  @property
  def lang_user(self):
    return self.bot.language_files.get(self.lang_code_user, self.bot.language_files["en"])

  @property
  def lang(self):
    return self.bot.language_files.get(self.lang_code, self.bot.language_files["en"])

  async def prompt(
          self,
          message: str,
          *,
          timeout: float = 60.0,
          delete_after: bool = True,
          author_id: Optional[int] = None,
          **kwargs
  ) -> Optional[bool]:
    """An interactive reaction confirmation dialog.

    Parameters
    -----------
    message: str
        The message to show along with the prompt.
    timeout: float
        How long to wait before returning.
    delete_after: bool
        Whether to delete the confirmation message after we're done.
    reacquire: bool
        Whether to release the database connection and then acquire it
        again when we're done.
    author_id: Optional[int]
        The member who should respond to the prompt. Defaults to the author of the
        Context's message.
    Returns
    --------
    Optional[bool]
        ``True`` if explicit confirm,
        ``False`` if explicit deny,
        ``None`` if deny due to timeout
    """
    author_id = author_id or self.author.id
    if self.author.bot and author_id == 892865928520413245:
      # unit testing bots can't use interactions :(
      return True
    view = ConfirmationView(
        timeout=timeout,
        delete_after=delete_after,
        ctx=self,
        author_id=author_id
    )
    kwargs["embed"] = kwargs.pop("embed", embed(title=message))
    view.message = await self.send(view=view, **kwargs)
    await view.wait()
    return view.value

  async def multi_select(self, message: str = "Please select one or more of the options.", options: List[dict] = [], *, values: list = [], emojis: list = [], descriptions: list = [], default: str = None, placeholder: str = None, min_values: int = 1, max_values: int = 1, timeout: float = 60.0, delete_after: bool = True, author_id: Optional[int] = None, **kwargs) -> Optional[list]:
    author_id = author_id or self.author.id
    view = MultiSelectView(
        options=options,
        # depricate this at some point
        values=values,
        emojis=emojis,
        descriptions=descriptions,
        default=default,
        # ############################
        placeholder=placeholder,
        timeout=timeout,
        min_values=min_values,
        max_values=max_values,
        ctx=self,
        delete_after=delete_after,
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

  async def edit(self, content: str | None = ..., embed: embed | None = ..., view: discord.ui.View | None = ...) -> discord.Message:
    if self.interaction:
      return await self.interaction.edit_original_response(content=content, embed=embed, view=view)
    if not self.bot_message:
      raise ValueError("Cannot edit a message that was not sent by the bot.")
    return await self.bot_message.edit(content=content, embed=embed, view=view)

  async def reply(self, *args: Any, **kwargs: Any) -> discord.Message:
    return await self.send(*args, **kwargs)

  async def send(self, *args: Any, webhook: Optional[discord.Webhook] = None, **kwargs: Any) -> discord.Message:
    if not hasattr(kwargs, "mention_author") and not self.interaction:
      kwargs.update({"mention_author": False})

    if webhook is not None:
      kwargs.pop("mention_author")
      return await webhook.send(*args, wait=True, **kwargs)

    reference = kwargs.pop("reference", self.replied_reference if self.command and self.replied_reference else self.message) if not self.interaction else None
    reference = reference or self.message
    if self.bot_permissions.read_message_history and reference in self.bot.cached_messages:
      try:
        self._bot_message = await super().send(
            *args,
            reference=reference,
            **kwargs
        )
        return self._bot_message
      except discord.HTTPException:
        self._bot_message = await super().send(
            *args,
            **kwargs)
        return self._bot_message

    self._bot_message = await super().send(
        *args,
        **kwargs)
    return self._bot_message

  async def safe_send(self, content: str, *, escape_mentions=True, **kwargs: Any) -> discord.Message:
    if escape_mentions:
      content = discord.utils.escape_mentions(content)

    if len(content) > 2000:
      fp = io.BytesIO(content.encode())
      kwargs.pop("file", None)
      return await self.send(file=discord.File(fp, filename="message_too_long.txt"), **kwargs)
    else:
      return await self.send(content, **kwargs)


class GuildContext(MyContext):
  author: discord.Member
  guild: discord.Guild
  channel: Union[discord.VoiceChannel, discord.TextChannel, discord.Thread]
  me: discord.Member
  prefix: str
