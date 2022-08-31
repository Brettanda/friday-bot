from __future__ import annotations

import json
from typing import TypeVar
from abc import ABCMeta, abstractmethod
from typing_extensions import Self

import discord

MISSING = discord.utils.MISSING

T = TypeVar("T")


class ForceRequiredAttributeDefinitionMeta(type):
  def __call__(cls, *args, **kwargs):
    class_object = type.__call__(cls, *args, **kwargs)
    class_object.check_required_attributes()
    return class_object

  def __new__(cls, name, bases, namespace):
    # if "check_required_attributes" not in namespace:
    #   raise TypeError(f"{name!r} must implement check_required_attributes()")
    return super().__new__(cls, name, bases, namespace)


class Struct:
  # def __init__(self) -> None:
  #   if not isinstance(self, Struct) and issubclass(self, Struct):
  #     for k, v in getattr(self, "__annotations__", {}).items():
  #       if getattr(self, k, MISSING) in (MISSING, None):
  #         raise TypeError("'{}' is missing from '{}'".format(k, self.__class__.__name__))

  @classmethod
  def from_dict(cls, dct: dict) -> Self:
    self = cls()
    for k, v in dct.items():
      if isinstance(v, dict):
        setattr(self, k, Struct.from_dict(v))
      else:
        setattr(self, k, v)
    return self

  def _pop_dicts(self) -> dict:
    dct = self.__class__.__dict__.copy()
    dct.pop('__annotations__', {})
    dct.pop('__module__', {})
    dct.pop('__qualname__', {})
    dct.pop('__doc__', {})
    dct.pop('__metaclass__', {})
    dct.pop('_abc_impl', {})
    dct.pop('__abstractmethods__', {})
    return dct

  def __iter__(self):
    for k, v in self._pop_dicts().items():
      if v is MISSING or v is None:
        raise TypeError("'{}' is missing from '{}'".format(k, self.__class__.__name__))
      if isinstance(v, Struct):
        yield k, dict(v)
      else:
        yield k, v

  def __getitem__(self, key: str):
    try:
      return getattr(self, key)
    except AttributeError as e:
      raise KeyError(e)

  def __repr__(self) -> str:
    keys = sorted(self._pop_dicts())
    items = ("{}={!r}".format(k, self._pop_dicts()[k]) for k in keys)
    return "{}({})".format(type(self).__name__, ", ".join(items))


class StructRequired(Struct, metaclass=ABCMeta):
  @abstractmethod
  def check_required_attributes(self) -> None:
    pass


class AppCommandParameterDefault(StructRequired):  # (Struct, metaclass=ForceRequiredAttributeDefinitionMeta):
  name: str = MISSING
  description: str = MISSING

  def check_required_attributes(self):
    if self.name is None:
      raise AttributeError(f"'name' is required for {self!r}")
    if self.description is None:
      raise AttributeError(f"'description' is required for {self!r}")


class CommandDefault(StructRequired):  # (Struct):
  help: str = MISSING

  def check_required_attributes(self):
    if self.help is MISSING:
      self.help = "..."


class AppCommandDefaultParameters(CommandDefault):  # , total=False):
  parameters: dict[str, AppCommandParameterDefault] | None = None


class AppCommandDefault(StructRequired):  # (Struct, metaclass=ForceRequiredAttributeDefinitionMeta):
  command_name: str = MISSING
  parameters: Struct = MISSING

  def check_required_attributes(self):
    if self.command_name is MISSING:
      raise AttributeError(f"'command_name' is required for {self!r}")


class CommandGroupDefault(CommandDefault):  # , metaclass=ForceRequiredAttributeDefinitionMeta):
  commands: Struct

  def check_required_attributes(self):
    if self.commands is None:
      raise AttributeError(f"'commands' is required for {self!r}")
    # else:
    #   for k, v in dict(self.commands).items():
    #     v.check_required_attributes()


class CommandGroupDefaultCustom(CommandDefault):
  ...


class AppCommandGroupDefault(CommandDefault):  # , metaclass = ForceRequiredAttributeDefinitionMeta):
  command_name: str = MISSING
  commands: Struct = MISSING

  def check_required_attributes(self):
    if self.command_name is MISSING:
      raise AttributeError(f"'command_name' is required for {self!r}")
    if self.commands is MISSING:
      raise AttributeError(f"'commands' is required for {self!r}")
    # else:
    #   for k, v in self.commands.items():
    #     v.check_required_attributes()


class AppCommandGroupDefaultCustom(CommandDefault):
  command_name: str = MISSING


class CogDefault(StructRequired):  # (Struct, metaclass=ForceRequiredAttributeDefinitionMeta):
  cog_description: str = MISSING

  def check_required_attributes(self):
    if self.cog_description is None:
      raise AttributeError(f"'cog_description' is required for {self!r}")


class ParameterChannel(AppCommandParameterDefault):
  name: str = "channel"
  description: str = "The channel where this will take effect"


class Errors(Struct):
  try_again_later: str = "This functionality is not currently available. Try again later?"
  canceled: str = "Canceled"


class Automodinvalid_punishments(Struct):
  _if: str = "The following punishments are invalid: "
  _else: str = "One or more of the punishments you provided is invalid."


class Automodroleorchannel(Struct):
  rolenotfound: str = "Role or channel not found."
  hierarchy: str = "Your role hierarchy is too low for this action."


class Automodwarned(Struct):
  title: str = "You have been warned"
  description: str = "You have been warned in `{}` for `{}`"


class Automodspamming_reasons(Struct):
  mentions: str = "Spamming mentions."
  content: str = "Spamming with content matching previous messages."
  messages: str = "Spamming messages."


class Automodwarn_theshold(Struct):
  reached: str = "Warn Threshold Reached"
  description: str = "You have passed `{}` warns for `{}`.\nYou have taken the punishment(s) `{}`."


class AutomodBlacklistAdd(Struct):
  badargument: str = "Word must be at least 3 characters long."
  dupe: str = "Can't add duplicate word"
  added: str = "Added `{}` to the blacklist"


class AutomodBlacklistRemove(Struct):
  doesntexist: str = "You don't seem to be blacklisting that word"
  removed: str = "Removed `{}` from the blacklist"


class AutomodBlacklistDisplay(Struct):
  doesntexist: str = "No blacklisted words yet, use `{}blacklist add <word>` to get started"
  words: str = "Blocked words"


class AutomodBlacklistPunishments(Struct):
  title: str = "Warning punishments"
  description: str = "The warning punishments for `{}` are `{}`."
  set: str = "Set punishment to `{}`"


class Automodblacklist(Struct):
  add = AutomodBlacklistAdd()
  remove = AutomodBlacklistRemove()
  display = AutomodBlacklistDisplay()
  punishments = AutomodBlacklistPunishments()
  clear: str = "Removed all blacklisted words"


class Automod(CogDefault):
  cog_description = "There are somethings in this world that bots are better at then humans. Let Friday help out with the moderation of your Discord server."
  invalid_punishments = Automodinvalid_punishments()
  roleorchannel = Automodroleorchannel()
  warned = Automodwarned()
  spamming_reasons = Automodspamming_reasons()
  prev_muted: str = "Member was previously muted."
  warn_theshold = Automodwarn_theshold()
  whitelist: str = "Whitelisted `{}`"
  unwhitelist: str = "Unwhitelisted `{}`"
  blacklist = Automodblacklist()


class Autorole(Struct):
  ...


class ChatRatelimitAdsVoting(Struct):
  message: str = "Get a higher message cap by voting on [Top.gg](https://top.gg/bot/476303446547365891/vote)."
  button: str = "Vote for more"


class ChatRatelimitAdsPatron(Struct):
  message: str = "Get the most powerful message cap by becoming a [Patron](https://patreon.com/join/fridaybot)."
  button: str = "Become a Patron for more"


class ChatRatelimitAds(Struct):
  voting = ChatRatelimitAdsVoting()
  streak: str = "Get an even higher cap by keeping a voting streak of at least 2 days."
  patron = ChatRatelimitAdsPatron()


class ChatRatelimit(Struct):
  title: str = "You have sent me over `{count}` in that last `{human}` and are being rate limited, try again {stamp}"
  ads = ChatRatelimitAds()


class ChatCommandTalkParametersMessage(Struct):
  name: str = "message"
  description: str = "Your message to Friday"


class ChatCommandTalkParameters(Struct):
  message = ChatCommandTalkParametersMessage()


class ChatCommandTalk(AppCommandDefault):
  command_name = "talk"
  help = "Chat with Friday, powered by GPT-3 and get a response."
  parameters = ChatCommandTalkParameters()


class ChatCommandReset(AppCommandDefault):
  command_name = "reset"
  help = "Resets Friday's chat history. Helps if Friday is repeating messages"


class ChatCommandsInfo(AppCommandDefault):
  command_name: str = "info"
  help: str = "Displays information about the current conversation"
  no_history: str = "No history found"
  response_title: str = "Chat Info"
  response_field_titles: list[str] = ["Messages", "Voted messages", "Voting Streak messages", "Patroned messages", "Recent history resets", "Message History"]
  response_rate: str = "{rate} remaining"


class ChatChatCommands(Struct):
  talk = ChatCommandTalk()
  info = ChatCommandsInfo()
  reset = ChatCommandReset()


class ChatChat(AppCommandGroupDefault):
  command_name: str = "chat"
  help: str = "Talk or get info about chatting with Friday"
  commands = ChatChatCommands()


class ChatChatChannelCommandsSetParameters(Struct):
  channel = ParameterChannel()


class ChatChatChannelCommandsSet(AppCommandDefault):
  command_name = "set"
  help = "Set the current channel so that I will always try to respond with something"
  parameters = ChatChatChannelCommandsSetParameters()


class ChatChatChannelCommandsWebhookParametersEnable(AppCommandParameterDefault):
  name = "enable"
  description = "Weather to enable or disable webhook mode"


class ChatChatChannelCommandsWebhookParameters(Struct):
  enable = ChatChatChannelCommandsWebhookParametersEnable()


class ChatChatChannelCommandsWebhook(AppCommandDefault):
  command_name = "webhook"
  help = "Toggles webhook chatting with Friday in the current chat channel"
  parameters = ChatChatChannelCommandsWebhookParameters()


class ChatChatChannelCommandsClear(AppCommandDefault):
  command_name = "clear"
  help = "Clear the current chat channel"


class ChatChatChannelCommands(Struct):
  set = ChatChatChannelCommandsSet()
  webhook = ChatChatChannelCommandsWebhook()
  clear = ChatChatChannelCommandsClear()


class ChatChatchannel(AppCommandGroupDefault):
  command_name = "chatchannel"
  help = "Display or change the channel where the bot will chat"
  commands = ChatChatChannelCommands()


class ChatPersona(AppCommandDefault):
  command_name: str = "persona"
  help: str = "Change Friday's persona"


class Chat(CogDefault):
  cog_description: str = "Chat with Friday, say something on Friday's behalf, and more with the chat commands."
  ratelimit = ChatRatelimit()
  flagged: str = "My response was flagged and could not be sent, please try again"
  no_response: str = "Somehow, I don't know what to say."
  try_again_later: str = "Something went wrong, please try again later"
  chat = ChatChat()
  chatchannel = ChatChatchannel()
  persona = ChatPersona()


class ConfigLanguage(Struct):
  invalid_lang: str = "Language {language} does not exist, or is not supported."


class ConfigUserLanguage(AppCommandDefault):
  command_name: str = "userlanguage"
  help: str = "My language to speak with just you. Doesn't affect application commands"
  select_title: str = "Select the language you would like me to speak"
  select_description: str = "If you find something wrong with the translations, please contribute on the [Crowdin page](https://crwd.in/fridaybot)\n\nKeep in mind that this gets overridden with application commands by the locale set by your client."
  current_lang: str = "Current language: `{current_language}`"
  new_lang: str = "New language set to: `{new_language}`"
  new_lang_desc: str = "Keep in mind that this gets overridden with application commands by the locale set by your client."


class ConfigServerLanguage(AppCommandDefault):
  command_name: str = "serverlanguage"
  help: str = "My default language to speak in a server. Doesn't affect application commands"
  select_title: str = "Select the language you would like me to speak"
  select_description: str = "If you find something wrong with the translations, please contribute on the [Crowdin page](https://crwd.in/fridaybot)\n\nKeep in mind that this gets overridden with application commands by the locale set by your client."
  current_lang: str = "Current language: `{current_language}`"
  new_lang: str = "New language set to: `{new_language}`"
  new_lang_desc: str = "Keep in mind that this gets overridden with application commands by the locale set by your client."


class ConfigPrefix(CommandDefault):
  help: str = "Sets the prefix for Fridays commands"
  new_prefix: str = "My new prefix is `{new_prefix}`"
  max_chars: str = "Can't set a prefix with more than 5 characters"


class ConfigBotChannel(CommandDefault):
  help: str = "The channel where bot commands live."
  title: str = "Bot Channel set"


class ConfigRestrictList(CommandDefault):
  help: str = "Lists the restricted commands"
  response_title: str = "Restricted Commands"
  response_no_commands: str = "No commands are restricted."


class ConfigRestrictCommands(Struct):
  list = ConfigRestrictList()


class ConfigRestrict(CommandGroupDefaultCustom):
  help: str = "Restricts the selected command to the bot channel. Ignored with manage server permission."
  title: str = "**{command_name}** has been restricted to the bot channel."
  commands = ConfigRestrictCommands()


class ConfigUnrestrict(CommandDefault):
  help: str = "Unrestricts the selected command."
  title: str = "**{command_name}** has been unrestricted."


class ConfigEnable(CommandDefault):
  help: str = "Enables the selected command(s)."
  title: str = "**{command_name}** has been enabled."


class ConfigDisable(CommandDefault):
  help: str = "Disable a command"
  title: str = "**{command_name}** has been disabled."


class ConfigDisableList(CommandDefault):
  help: str = "Lists all disabled commands."
  title: str = "Disabled Commands"
  none_found: str = "There are no disabled commands."


class ConfigUpdatesParameters(Struct):
  channel = ParameterChannel()


class ConfigUpdates(AppCommandDefault):
  command_name: str = "updates"
  help: str = "Recieve updates on new features and changes for Friday"
  prompt: str = "This channel is already subscribed to updates. Are you sure you want to subscribe again?"
  cancelled: str = "Cancelled"
  reason: str = "Called updates command, for Friday updates"
  followed: str = "Updates channel followed"
  parameters = ConfigUpdatesParameters()


class Config(CogDefault):
  cog_description = "The general configuration commands for Friday"
  language = ConfigLanguage()
  userlanguage = ConfigUserLanguage()
  serverlanguage = ConfigServerLanguage()
  prefix = ConfigPrefix()
  botchannel = ConfigBotChannel()
  botchannelclear = str()
  restrict = ConfigRestrict()
  unrestrict = ConfigUnrestrict()
  enable = ConfigEnable()
  disable = ConfigDisable()
  disablelist = ConfigDisableList()
  updates = ConfigUpdates()


class Dbl(Struct):
  ...


class DiceDiceParametersRoll(AppCommandParameterDefault):
  name: str = "roll"
  description: str = "..."


class DiceDiceParameters(Struct):
  roll = DiceDiceParametersRoll()


class DiceDice(AppCommandDefault):
  command_name: str = "dice"
  help: str = "..."
  response_title: str = "Your total: {total}"
  response_description: str = "Query: {query}\nResult: {result}"
  parameters = DiceDiceParameters()


class Dice(CogDefault):
  cog_description: str = "Roll some dice with advantage or just do some basic math."
  dice = DiceDice()


class FunPollMessageParameter(AppCommandParameterDefault):
  name: str = "poll_message"
  description: str = "The target poll message to be modified"


class FunPollMessageParameters(Struct):
  poll_message = FunPollMessageParameter()


class FunPollCommandsCreate(AppCommandDefault):
  command_name: str = "create"
  help: str = "Make a poll for users to vote on"


class FunPollCommandsEdit(AppCommandDefault):
  command_name: str = "edit"
  help: str = "Edit an existing poll that you created"
  parameters = FunPollMessageParameters()


class FunPollCommandsDelete(AppCommandDefault):
  command_name: str = "delete"
  help: str = "Delete an existing poll that you created"
  parameters = FunPollMessageParameters()


class FunPollCommandsEnd(AppCommandDefault):
  command_name: str = "end"
  help: str = "Conclude an existing poll that you created"
  parameters = FunPollMessageParameters()


class FunPollCommands(Struct):
  create = FunPollCommandsCreate()
  edit = FunPollCommandsEdit()
  delete = FunPollCommandsDelete()
  end = FunPollCommandsEnd()


class FunPollModal(Struct):
  title: str = "Create or edit a poll"


class FunPoll(AppCommandGroupDefault):
  command_name: str = "poll"
  help: str = "Create a poll"
  commands = FunPollCommands()
  modal = FunPollModal()


class FunRockPaperScissorsParameter(AppCommandParameterDefault):
  name: str = "choice"
  description: str = "The choice to be made"


class FunRockPaperScissorsParameters(Struct):
  choice = FunRockPaperScissorsParameter()


class FunRockPaperScissorsChoices(Struct):
  rock: str = "Rock"
  paper: str = "Paper"
  scissors: str = "Scissors"


class FunRockPaperScissorsWinOptions(Struct):
  draw: str = "Draw"
  error: str = "Something went wrong"


class FunRockPaperScissors(AppCommandDefault):
  command_name: str = "rockpaperscissors"
  help: str = "Play Rock Paper Scissors with Friday"
  parameters = FunRockPaperScissorsParameters()
  choices = FunRockPaperScissorsChoices()
  win_options = FunRockPaperScissorsWinOptions()
  response_title: str = "Your move: {user_choice} VS My move: {bot_choice}"
  response_description: str = "The winner of this round is: **{winner_user_name}**"


class FunMinesweeperParametersSize(AppCommandParameterDefault):
  name: str = "size"
  description: str = "The size of the grid"


class FunMinesweeperParametersBombCount(AppCommandParameterDefault):
  name: str = "bomb_count"
  description: str = "The number of bombs to be placed"


class FunMinesweeperParameters(Struct):
  size = FunMinesweeperParametersSize()
  bomb_count = FunMinesweeperParametersBombCount()


class FunMinesweeper(AppCommandDefault):
  command_name: str = "minesweeper"
  help: str = "Play Minesweeper"
  response_title: str = "{size}x{size} with {bomb_count} bombs"
  response_author: str = "Minesweeper"
  parameters = FunMinesweeperParameters()
  error_max_board_size: str = "Size cannot be larger than 9 due to the message character limit of Discord"
  error_greater_than_board: str = "Bomb count cannot be larger than the game board"
  error_greater_than_one: str = "Bomb count and board size must be greater than 1"


class Fun(CogDefault):
  cog_description: str = "Fun games and other commands to give more life to your Discord server."
  poll = FunPoll()
  rockpaperscissors = FunRockPaperScissors()
  minesweeper = FunMinesweeper()


class GeneralInvite(AppCommandDefault):
  command_name: str = "invite"
  help: str = "Get the invite link to add me to your server"


class GeneralAbout(AppCommandDefault):
  command_name: str = "about"
  help: str = "Displays some information about myself :)"
  response_title: str = "{bot_name} - About"
  response_description: str = "Big thanks to all Patrons!"
  response_field_titles: list[str] = [
      "Servers joined",
      "Latency",
      "Shards",
      "Loving Life",
      "Uptime",
      "CPU/RAM",
      "Existed since"
  ]
  response_field_values: list[str] = [
      "{ping} ms",
      "True",
      "{memory_usage} MiB\n{cpu_usage}% CPU"
  ]
  response_footer: str = "Made with ❤️ and discord.py!"


class General(CogDefault):
  cog_description: str = "Some general commands"
  invite = GeneralInvite()
  about = GeneralAbout()


class Help(CogDefault):
  cog_description: str = "If you would like to make a suggestion for a command please join the [Friday's Development](https://discord.gg/NTRuFjU) and explain your suggestion.\n\nFor more info on how commands work and how to format them please check out [docs.friday-bot.com](https://docs.friday-bot.com/).\n\n**Some commands will only show if you have the correct permissions to use them.**"
  no_help: str = "No help found..."
  examples: str = "Examples"
  signature: str = "Signature"
  params: str = "Available Parameters"
  commands: str = "Commands"
  no_permissible_commands: str = "No commands that you can use"


class Issue(Struct):
  ...


class Log(Struct):
  ...


class Logging(Struct):
  ...


class Meme(Struct):
  ...


class Moderation(Struct):
  ...


class Music(Struct):
  ...


class PingPing(AppCommandDefault):
  command_name: str = "ping"
  help: str = "Pong!"
  response_title: str = "Pong!"
  response_description: str = "⏳ API is {ping}ms"


class Ping(CogDefault):
  cog_description: str = "Ping? Pong!"
  ping = PingPing()


class Redditlink(Struct):
  ...


class Reminder(Struct):
  ...


class SupportSupport(AppCommandDefault):
  command_name: str = "support"
  help: str = "Get an invite link to my support server"


class SupportDonate(AppCommandDefault):
  command_name: str = "donate"
  help: str = "Get the Patreon link for Friday"


class Support(CogDefault):
  cog_description: str = "Some support commands"
  support = SupportSupport()
  donate = SupportDonate()


class Welcome(Struct):
  ...


class Nacl(Struct):
  ...


class Dev(Struct):
  ...


class Ipc(Struct):
  ...


class Topgg(Struct):
  ...


class Modlogging(Struct):
  ...


class Database(Struct):
  ...


class Datedevents(Struct):
  ...


class Sharding(Struct):
  ...


class Stats(Struct):
  ...


class Scheduledevents(Struct):
  ...


class Patreons(Struct):
  ...


class Api(Struct):
  ...


class Stars(Struct):
  ...


class Choosegame(Struct):
  ...


class I18n(Struct):
  _lang_name: str = "English"
  _lang_emoji: str = "🇺🇸"
  _translator: str = "Motostar#0001"
  errors = Errors()
  automod = Automod()
  autorole = Autorole()
  chat = Chat()
  config = Config()
  dbl = Dbl()
  dice = Dice()
  fun = Fun()
  general = General()
  help = Help()
  issue = Issue()
  log = Log()
  logging = Logging()
  meme = Meme()
  moderation = Moderation()
  music = Music()
  ping = Ping()
  redditlink = Redditlink()
  reminder = Reminder()
  support = Support()
  welcome = Welcome()
  nacl = Nacl()
  dev = Dev()
  ipc = Ipc()
  topgg = Topgg()
  modlogging = Modlogging()
  database = Database()
  datedevents = Datedevents()
  sharding = Sharding()
  stats = Stats()
  scheduledevents = Scheduledevents()
  patreons = Patreons()
  api = Api()
  stars = Stars()
  choosegame = Choosegame()


en = I18n()
print(en.ping.ping.command_name)

with open("./i18n/en/commands.json", "w") as f:
  d = dict(en)
  f.write(json.dumps(d, indent=4, ensure_ascii=False))
