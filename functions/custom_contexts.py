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
      if not self.message.flags.ephemeral:
        await self.message.delete()
      else:
        await self.message.edit(view=None, content=None, embeds=[Embed(title="This is safe to dismiss now")])

  @discord.ui.button(emoji="\N{HEAVY CHECK MARK}", label='Confirm', custom_id="confirmation_true", style=discord.ButtonStyle.green)
  async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
    self.value = True
    await interaction.response.defer()
    if self.delete_after and self.message:
      if not self.message.flags.ephemeral:
        await self.message.delete()
      else:
        await self.message.edit(view=None, content=None, embeds=[Embed(title="This is safe to dismiss now")])
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
    if self.delete_after and self.message:
      if not self.message.flags.ephemeral:
        await self.message.delete()
      else:
        await self.message.edit(view=None, content=None, embeds=[Embed(title="This is safe to dismiss now")])
    self.stop()

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if interaction.user and interaction.user.id == self.author_id:
      return True
    else:
      await interaction.response.send_message('This confirmation dialog is not for you.', ephemeral=True)
      return False

  async def on_timeout(self) -> None:
    if self.delete_after and self.message:
      if not self.message.flags.ephemeral:
        await self.message.delete()
      else:
        await self.message.edit(view=None, content=None, embeds=[Embed(title="This is safe to dismiss now")])


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
  def lang_user(self) -> I18n:
    return self.bot.language_files.get(self.lang_code_user, self.bot.language_files["en"])

  @property
  def lang(self) -> I18n:
    return self.bot.language_files.get(self.lang_code, self.bot.language_files["en"])

  async def prompt(
          self,
          message: str,
          *,
          embed: Optional[Embed] = None,
          timeout: float = 60.0,
          delete_after: bool = True,
          author_id: Optional[int] = None,
          **kwargs
  ) -> Optional[bool]:
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
    embed = embed or Embed(title=message)
    view.message = await self.send(view=view, embed=embed, **kwargs)
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
