from discord.ext.commands import CommandError


class UserNotInVoiceChannel(CommandError):
  def __init__(self, message="You must be in a voice channel to use this command"):
    self.message = message
    super().__init__(self.message)

  def __str__(self):
    return f"{self.message}"


class NoCustomSoundsFound(CommandError):
  def __init__(self, message="This server has not custom sounds saved yet"):
    self.message = message
    super().__init__(self.message)

  def __str__(self):
    return f"{self.message}"


class ArgumentTooLarge(CommandError):
  def __init__(self, message="That argument number is too big"):
    self.message = message
    super().__init__(self.message)

  def __str__(self):
    return f"{self.message}"


class CantSeeNewVoiceChannelType(CommandError):
  def __init__(self, message="That argument number is too big"):
    self.message = message
    super().__init__(self.message)

  def __str__(self):
    return f"{self.message}"
