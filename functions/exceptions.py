from discord.ext.commands import CommandError
from discord_slash.error import SlashCommandError


class Base(CommandError):
  def __init__(self, message=None, *args, **kwargs):
    super().__init__(message=message, *args, **kwargs)

  def __str__(self):
    return super().__str__()


class SlashBase(SlashCommandError):
  def __init__(self, message=None, *args, **kwargs):
    super().__init__(message=message, *args, **kwargs)

  def __str__(self):
    return super().__str__()


class UserNotInVoiceChannel(Base):
  def __init__(self, message="You must be in a voice channel to use this command"):
    super().__init__(message=message)


class NoCustomSoundsFound(Base):
  def __init__(self, message="This server has not custom sounds saved yet"):
    super().__init__(message=message)


class ArgumentTooLarge(Base):
  def __init__(self, message="That argument number is too big"):
    super().__init__(message=message)


class CantSeeNewVoiceChannelType(Base):
  def __init__(self, message="I believe you are in a new type of voice channel that I can't join yet"):
    super().__init__(message=message)


class OnlySlashCommands(SlashBase):
  def __init__(self, message="I need to be added to this server with my bot account for this command to work. Please use the link found on <https://friday-bot.com>"):
    super().__init__(message)
