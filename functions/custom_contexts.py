from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any, Generator, List, Optional, Tuple, Union

import discord
from discord.context_managers import Typing as TypingOld
from discord.ext import commands

from .myembed import embed

if TYPE_CHECKING:
  from aiohttp import ClientSession
  from asyncpg import Connection, Pool

  from functions.config import ReadOnly
  from index import Friday


class Typing(TypingOld):
  async def __aenter__(self) -> None:
    try:
      await super().__aenter__()
    except discord.Forbidden:
      pass


class ConfirmationView(discord.ui.View):
  def __init__(self, *, timeout: float, author_id: int, reacquire: bool, ctx: MyContext, delete_after: bool) -> None:
    super().__init__(timeout=timeout)
    self.value: Optional[bool] = None
    self.delete_after: bool = delete_after
    self.author_id: int = author_id
    self.ctx: MyContext = ctx
    self.reacquire: bool = reacquire
    self.message: Optional[discord.Message] = None

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if interaction.user and interaction.user.id == self.author_id:
      return True
    else:
      await interaction.response.send_message('This confirmation dialog is not for you.', ephemeral=True)
      return False

  async def on_timeout(self) -> None:
    if self.reacquire:
      await self.ctx.acquire()
    if self.delete_after and self.message:
      await self.message.delete()

  @discord.ui.button(emoji="\N{HEAVY CHECK MARK}", label='Confirm', custom_id="confirmation_true", style=discord.ButtonStyle.green)
  async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
    self.value = True
    await interaction.response.defer()
    if self.delete_after:
      await interaction.delete_original_message()
    self.stop()

  @discord.ui.button(emoji="\N{HEAVY MULTIPLICATION X}", label='Cancel', custom_id="confirmation_false", style=discord.ButtonStyle.red)
  async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
    self.value = False
    await interaction.response.defer()
    if self.delete_after:
      await interaction.delete_original_message()
    self.stop()


class MultiSelectView(discord.ui.View):
  def __init__(self, options: list, *, values: list = [], emojis: list = [], descriptions: list = [], placeholder: str = None, min_values: int = 1, max_values: int = 1, default: str = None, timeout: float, delete_after: bool, reacquire: bool, author_id: int, ctx: MyContext) -> None:
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
    self.reacquire: bool = reacquire
    self.delete_after: bool = delete_after
    self.message: Optional[discord.Message] = None

    self.values: Optional[list] = None

    self.select.options = self.options
    self.select.placeholder = self.placeholder
    self.select.min_values = self.min_values
    self.select.max_values = self.max_values

  @discord.ui.select(custom_id="prompt_select", options=[discord.SelectOption(label="Loading...")], min_values=0, max_values=0)
  async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
    self.values = select.data["values"]  # type: ignore
    if self.delete_after:
      await interaction.delete_original_message()
    self.stop()

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if interaction.user and interaction.user.id == self.author_id:
      return True
    else:
      await interaction.response.send_message('This confirmation dialog is not for you.', ephemeral=True)
      return False

  async def on_timeout(self) -> None:
    if self.reacquire:
      await self.ctx.acquire()
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

class _ContextDBAcquire:
  __slots__ = ("ctx", "timeout")

  def __init__(self, ctx: MyContext, timeout: Optional[float]):
    self.ctx: MyContext = ctx
    self.timeout: Optional[float] = timeout

  def __await__(self) -> Generator[Any, None, Connection]:
    return self.ctx._acquire(self.timeout).__await__()

  async def __aenter__(self) -> Union[Pool, Connection]:
    await self.ctx._acquire(self.timeout)
    return self.ctx.db

  async def __aexit__(self, *args) -> None:
    await self.ctx.release()


class MyContext(commands.Context):
  channel: Union[discord.VoiceChannel, discord.TextChannel, discord.Thread, discord.DMChannel]
  prefix: str
  command: commands.Command[Any, ..., Any]
  bot: Friday

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.pool: Pool = self.bot.pool
    self._db: Optional[Union[Pool, Connection]] = None
    name: str = "en"
    self._lang: Tuple[str, ReadOnly[dict[str, Any]]] = (name, self.bot.langs["en"])
    self._lang_default = self._lang

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
  def db(self) -> Union[Pool, Connection]:
    return self._db if self._db else self.pool

  async def _acquire(self, timeout: Optional[float]) -> Connection:
    if self._db is None:
      self._db = await self.pool.acquire(timeout=timeout)
    return self._db

  def acquire(self, *, timeout=300.0) -> _ContextDBAcquire:
    """Acquires a database connection from the pool. e.g. ::
          async with ctx.acquire():
              await ctx.db.execute(...)
      or: ::
          await ctx.acquire()
          try:
              await ctx.db.execute(...)
          finally:
              await ctx.release()
    """
    return _ContextDBAcquire(self, timeout)

  async def release(self) -> None:
    """Releases the database connection from the pool.
      Useful if needed for "long" interactive commands where
      we want to release the connection and re-acquire later.
      Otherwise, this is called automatically by the bot.
      """
    # from source digging asyncpg source, releasing an already
    # released connection does nothing

    if self._db is not None:
      await self.bot.pool.release(self._db)
      self._db = None

  def typing(self, **kwargs: Any):
    if self.interaction:
      return Typing(self)
    return super().typing(**kwargs)

  @property
  def lang(self):
    return self._lang

  async def get_lang(self):
    if not self.guild:
      return ("en", self.bot.langs["en"])
    conf = await self.bot.log.get_guild_config(self.guild.id, connection=self.db)
    self._lang = (conf.lang, self.bot.langs.get(conf.lang, "en"))  # type: ignore
    return self._lang

    # if msg.guild is None:
    #   return self.langs["en"]
    # if not self.log:
    #   return self.langs.get(msg.guild.preferred_locale[:2], "en")
    # return self.langs.get((await self.log.get_guild_config(msg.guild.id)).lang)

  async def prompt(
          self,
          message: str,
          *,
          timeout: float = 60.0,
          delete_after: bool = True,
          reacquire: bool = True,
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
        reacquire=reacquire,
        ctx=self,
        author_id=author_id
    )
    kwargs["embed"] = kwargs.pop("embed", embed(title=message))
    view.message = await self.send(view=view, **kwargs)
    await view.wait()
    return view.value

  async def multi_select(self, message: str = "Please select one or more of the options.", options: List[dict] = [], *, values: list = [], emojis: list = [], descriptions: list = [], default: str = None, placeholder: str = None, min_values: int = 1, max_values: int = 1, timeout: float = 60.0, delete_after: bool = True, reacquire: bool = True, author_id: Optional[int] = None, **kwargs) -> Optional[list]:
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
        reacquire=reacquire,
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

  async def reply(self, *args, **kwargs) -> discord.Message:
    return await self.send(*args, **kwargs)

  async def send(self, *args, **kwargs) -> discord.Message:
    if not hasattr(kwargs, "mention_author") and not self.interaction:
      kwargs.update({"mention_author": False})
    reference = self.replied_reference if self.command and self.replied_reference else self.message
    try:
      return await super().send(
          *args,
          reference=reference,
          **kwargs
      )
    except (discord.Forbidden, discord.HTTPException) as e:
      if self.interaction:
        raise e
      try:
        return await self.message.channel.send(*args, **kwargs)
      except (discord.Forbidden, discord.HTTPException):
        raise e

  async def safe_send(self, content: str, *, escape_mentions=True, **kwargs) -> discord.Message:
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
