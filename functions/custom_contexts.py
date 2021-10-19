from discord_slash import SlashContext
from discord.ext.commands import Context
import discord
import io
import typing
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday as Bot


class MySlashContext(SlashContext):
  def __init__(self):
    self.reply = self.reply

  async def reply(self, content=None, **kwargs):
    await self.send(content, **kwargs)
    # if not hasattr(kwargs,"delete_after") and self.command.name not in ["meme","issue","reactionrole","minesweeper"]:
    #   delete = await get_delete_time(self)
    #   delete = delete if delete is not None and delete != 0 else None
    #   if delete != None:
    #     kwargs.update({"delete_after":delete})
    #     await self.message.delete(delay=delete)
    # try:
    #   return await self.message.reply(content,**kwargs)
    # except discord.Forbidden as e:
    #   if "Cannot reply without permission" in str(e):
    #     return await self.message.channel.send(content,**kwargs)
    #   else:
    #     raise e
    # except discord.HTTPException as e:
    #   if "Unknown message" in str(e):
    #     return await self.message.channel.send(content,**kwargs)
    #   else:
    #     raise e


class FakeInteractionMessage:
  """Turns an `discord.Interaction` into sudo a `discord.Message`"""

  def __init__(self, bot: "Bot", interaction: discord.Interaction):
    self._bot = bot
    self.interaction = interaction
    super().__init__()

  @property
  def bot(self) -> typing.Union["Bot", discord.Client, discord.AutoShardedClient]:
    return self._bot

  @property
  def channel(self) -> typing.Union[discord.TextChannel, discord.DMChannel]:
    return self.interaction.channel

  @property
  def guild(self) -> discord.Guild:
    return self.interaction.guild

  @property
  def author(self) -> typing.Union[discord.User, discord.Member]:
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


class MyContext(Context):
  @property
  def db(self):
    return self.bot.db

  def is_interaction(self) -> bool:
    return isinstance(self.message, FakeInteractionMessage)

  async def reply(self, content: str = None, *, delete_original: bool = False, **kwargs) -> typing.Union[discord.Message, FakeInteractionMessage]:
    ignore_coms = ["log", "help", "meme", "issue", "reactionrole", "minesweeper", "poll", "confirm", "souptime", "say", "countdown"]
    if not hasattr(kwargs, "delete_after") and self.command is not None and self.command.name not in ignore_coms and self.message.type.name != "application_command":
      if hasattr(self.bot, "get_guild_delete_commands"):
        delete = self.bot.log.get_guild_delete_commands(self.message.guild)
      else:
        delete = None
      delete = delete if delete is not None and delete != 0 else None
      if delete is not None and self.command.name not in ignore_coms:
        kwargs.update({"delete_after": delete})
        await self.message.delete(delay=delete)
    if not hasattr(kwargs, "mention_author") and self.message.type.name != "application_command":
      kwargs.update({"mention_author": False})
    try:
      if self.is_interaction():
        kwargs.pop("delete_after", None)
        if self.message.interaction.response.is_done():
          return await self.message.interaction.followup.send(content, **kwargs)
        return await self.message.interaction.response.send_message(content, **kwargs)
      if self.message.type == discord.MessageType.thread_starter_message:
        return await self.message.channel.send(content, **kwargs)
      return await self.message.reply(content, **kwargs)
    except (discord.Forbidden, discord.HTTPException):
      try:
        if self.is_interaction():
          kwargs.pop("delete_after", None)
          if self.message.interaction.response.is_done():
            return await self.message.interaction.followup.send(content, **kwargs)
          return await self.message.interaction.response.send_message(content, **kwargs)
        return await self.message.channel.send(content, **kwargs)
      except (discord.Forbidden, discord.HTTPException):
        pass

  async def send(self, content: str = None, *, delete_original: bool = False, **kwargs) -> typing.Union[discord.Message, FakeInteractionMessage]:
    return await self.reply(content, delete_original=delete_original, **kwargs)

  async def safe_send(self, content: str, *, escape_mentions=True, **kwargs) -> typing.Optional[typing.Union[discord.Message, FakeInteractionMessage]]:
    if escape_mentions:
      content = discord.utils.escape_mentions(content)

    if len(content) > 2000:
      fp = io.BytesIO(content.encode())
      kwargs.pop("file", None)
      return await self.send(file=discord.File(fp, filename="message_too_long.txt"), **kwargs)
    else:
      return await self.send(content, **kwargs)
