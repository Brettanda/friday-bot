from discord.ext.commands import CommandError
# from discord_slash.error import SlashCommandError


class Base(CommandError):
  def __init__(self, message=None, *args, **kwargs):
    self.log = False
    super().__init__(message=message, *args, **kwargs)

  def __str__(self):
    return super().__str__()


# class SlashBase(SlashCommandError):
#   def __init__(self, message=None, *args, **kwargs):
#     super().__init__(message=message, *args, **kwargs)

#   def __str__(self):
#     return super().__str__()


class UserNotInVoiceChannel(Base):
  def __init__(self, message="You must be in a voice channel to use this command", *args, **kwargs):
    super().__init__(message=message, *args, **kwargs)


class NoCustomSoundsFound(Base):
  def __init__(self, message="This server has not custom sounds saved yet", *args, **kwargs):
    super().__init__(message=message, *args, **kwargs)


class ArgumentTooLarge(Base):
  def __init__(self, message="That argument number is too big", *args, **kwargs):
    super().__init__(message=message, *args, **kwargs)


class CantSeeNewVoiceChannelType(Base):
  def __init__(self, message="I believe you are in a new type of voice channel that I can't join yet", *args, **kwargs):
    super().__init__(message=message, *args, **kwargs)


class OnlySlashCommands(Base):
  """ An exception for when I have been added to a server without a bot user"""

  def __init__(self, message="I need to be added to this server with my bot account for this command to work. Please use the link found on <https://friday-bot.com>", *args, **kwargs):
    super().__init__(message=message, *args, **kwargs)


class NotSupporter(Base):
  def __init__(self, message="You need to be a Patreon supporter to use this command.", *args, **kwargs):
    super().__init__(message=message, *args, **kwargs)


class RequiredTier(Base):
  def __init__(self, message="You do not have the required Patreon tier for this command.", *args, **kwargs):
    super().__init__(message=message, *args, **kwargs)


class NotInSupportServer(Base):
  def __init__(self, message="You need to be in my support server for this command.", *args, **kwargs):
    super().__init__(message=message, *args, **kwargs)
