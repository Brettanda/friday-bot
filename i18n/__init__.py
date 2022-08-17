from __future__ import annotations

import json
from typing import TypedDict


class AppCommandParameterDefault(TypedDict):
  name: str
  description: str


class CommandDefault(TypedDict, total=True):
  help: str


class AppCommandDefaultParameters(CommandDefault, total=False):
  parameters: dict[str, AppCommandParameterDefault]


class AppCommandDefault(AppCommandDefaultParameters, total=True):
  command_name: str


class CommandGroupDefault(CommandDefault):
  commands: dict[str, CommandDefault]


class CommandGroupDefaultCustom(CommandDefault):
  ...


class AppCommandGroupDefault(CommandDefault):
  command_name: str
  commands: dict[str, AppCommandDefault]


class AppCommandGroupDefaultCustom(CommandDefault):
  command_name: str


class CogDefault(TypedDict):
  cog_description: str


class Errors(TypedDict):
  try_again_later: str
  canceled: str


class Automodinvalid_punishments(TypedDict):
  _if: str
  _else: str


class Automodroleorchannel(TypedDict):
  rolenotfound: str
  hierarchy: str


class Automodwarned(TypedDict):
  title: str
  description: str


class Automodspamming_reasons(TypedDict):
  mentions: str
  content: str
  messages: str


class Automodwarn_theshold(TypedDict):
  reached: str
  description: str


class AutomodBlacklistAdd(TypedDict):
  badargument: str
  dupe: str
  added: str


class AutomodBlacklistRemove(TypedDict):
  doesntexist: str
  removed: str


class AutomodBlacklistDisplay(TypedDict):
  doesntexist: str
  words: str


class AutomodBlacklistPunishments(TypedDict):
  title: str
  description: str
  set: str


class Automodblacklist(TypedDict):
  add: AutomodBlacklistAdd
  remove: AutomodBlacklistRemove
  display: AutomodBlacklistDisplay
  punishments: AutomodBlacklistPunishments
  clear: str


class Automod(CogDefault):
  invalid_punishments: Automodinvalid_punishments
  roleorchannel: Automodroleorchannel
  warned: Automodwarned
  spamming_reasons: Automodspamming_reasons
  prev_muted: str
  warn_theshold: Automodwarn_theshold
  whitelist: str
  unwhitelist: str
  blacklist: Automodblacklist


class Autorole(TypedDict):
  ...


class ChatRatelimitAdsAd(TypedDict):
  message: str
  button: str


class ChatRatelimitAds(TypedDict):
  voting: ChatRatelimitAdsAd
  streak: str
  patron: ChatRatelimitAdsAd


class ChatRatelimit(TypedDict):
  title: str
  ads: ChatRatelimitAds


class ChatCommandsInfo(AppCommandDefault):
  no_history: str
  response_title: str
  response_field_titles: list[str]
  response_rate: str


class ChatChatCommands(TypedDict):
  talk: AppCommandDefault
  reset: AppCommandDefault
  info: ChatCommandsInfo


class ChatChat(CommandDefault):
  command_name: str
  commands: ChatChatCommands


class ChatChatchannel(AppCommandGroupDefault):
  ...


class ChatPersona(AppCommandDefault):
  ...


class Chat(CogDefault):
  ratelimit: ChatRatelimit
  flagged: str
  no_response: str
  try_again_later: str
  chat: ChatChat
  chatchannel: ChatChatchannel
  persona: ChatPersona


class ConfigLanguage(TypedDict):
  invalid_lang: str


class ConfigUserLanguage(AppCommandDefault):
  current_lang: str
  new_lang: str
  new_lang_desc: str
  select_title: str
  select_description: str


class ConfigServerLanguage(AppCommandDefault):
  current_lang: str
  new_lang: str
  new_lang_desc: str
  select_title: str
  select_description: str


class ConfigPrefix(CommandDefault):
  new_prefix: str
  max_chars: str


class ConfigBotChannel(CommandDefault):
  title: str


class ConfigRestrictList(CommandDefault):
  response_title: str
  response_no_commands: str


class ConfigRestrictCommands(TypedDict):
  list: ConfigRestrictList


class ConfigRestrict(CommandGroupDefaultCustom):
  title: str
  commands: ConfigRestrictCommands


class ConfigUnrestrict(CommandDefault):
  title: str


class ConfigEnable(CommandDefault):
  title: str


class ConfigDisable(CommandDefault):
  title: str


class ConfigDisableList(CommandDefault):
  title: str
  none_found: str


class ConfigUpdates(AppCommandDefault):
  prompt: str
  cancelled: str
  reason: str
  followed: str


class Config(CogDefault):
  language: ConfigLanguage
  userlanguage: ConfigUserLanguage
  serverlanguage: ConfigServerLanguage
  prefix: ConfigPrefix
  botchannel: ConfigBotChannel
  botchannelclear: str
  restrict: ConfigRestrict
  unrestrict: ConfigUnrestrict
  enable: ConfigEnable
  disable: ConfigDisable
  disablelist: ConfigDisableList
  updates: ConfigUpdates


class Dbl(TypedDict):
  ...


class DiceDice(AppCommandDefault):
  response_title: str
  response_description: str


class Dice(CogDefault):
  dice: DiceDice


class Fun(TypedDict):
  ...


class GeneralInvite(AppCommandDefault):
  ...


class General(CogDefault):
  invite: GeneralInvite


class Help(CogDefault):
  no_help: str
  examples: str
  signature: str
  params: str
  commands: str
  no_permissible_commands: str


class Issue(TypedDict):
  ...


class Log(TypedDict):
  ...


class Logging(TypedDict):
  ...


class Meme(TypedDict):
  ...


class Moderation(TypedDict):
  ...


class Music(TypedDict):
  ...


class PingPing(AppCommandDefault):
  response_title: str
  response_description: str


class Ping(CogDefault):
  ping: PingPing


class Redditlink(TypedDict):
  ...


class Reminder(TypedDict):
  ...


class SupportSupport(AppCommandDefault):
  ...


class SupportDonate(AppCommandDefault):
  ...


class Support(TypedDict):
  support: SupportSupport
  donate: SupportDonate


class Welcome(TypedDict):
  ...


class Nacl(TypedDict):
  ...


class Dev(TypedDict):
  ...


class Ipc(TypedDict):
  ...


class Topgg(TypedDict):
  ...


class Modlogging(TypedDict):
  ...


class Database(TypedDict):
  ...


class Datedevents(TypedDict):
  ...


class Sharding(TypedDict):
  ...


class Stats(TypedDict):
  ...


class Scheduledevents(TypedDict):
  ...


class Patreons(TypedDict):
  ...


class Api(TypedDict):
  ...


class Stars(TypedDict):
  ...


class Choosegame(TypedDict):
  ...


class I18n(TypedDict):
  _lang_name: str
  _lang_emoji: str
  _translator: str
  errors: Errors
  automod: Automod
  autorole: Autorole
  chat: Chat
  config: Config
  dbl: Dbl
  dice: Dice
  fun: Fun
  general: General
  help: Help
  issue: Issue
  log: Log
  logging: Logging
  meme: Meme
  moderation: Moderation
  music: Music
  ping: Ping
  redditlink: Redditlink
  reminder: Reminder
  support: Support
  welcome: Welcome
  nacl: Nacl
  dev: Dev
  ipc: Ipc
  topgg: Topgg
  modlogging: Modlogging
  database: Database
  datedevents: Datedevents
  sharding: Sharding
  stats: Stats
  scheduledevents: Scheduledevents
  patreons: Patreons
  api: Api
  stars: Stars
  choosegame: Choosegame


en = I18n(
    _lang_name="English",
    _lang_emoji="🇺🇸",
    _translator="Motostar#0001",
    errors=Errors(
        try_again_later="This functionality is not currently available. Try again later?",
        canceled="Canceled"
    ),
    automod=Automod(
        cog_description="There are somethings in this world that bots are better at then humans. Let Friday help out with the moderation of your Discord server.",
        invalid_punishments=Automodinvalid_punishments(
            _if="The following punishments are invalid: ",
            _else="One or more of the punishments you provided is invalid."
        ),
        roleorchannel=Automodroleorchannel(
            rolenotfound="Role or channel not found.",
            hierarchy="Your role hierarchy is too low for this action."
        ),
        warned=Automodwarned(
            title="You have been warned",
            description="You have been warned in `{}` for `{}`"
        ),
        spamming_reasons=Automodspamming_reasons(
            mentions="Spamming mentions.",
            content="Spamming with content matching previous messages.",
            messages="Spamming messages."
        ),
        prev_muted="Member was previously muted.",
        warn_theshold=Automodwarn_theshold(
            reached="Warn Threshold Reached",
            description="You have passed `{}` warns for `{}`.\nYou have taken the punishment(s) `{}`."
        ),
        whitelist="Whitelisted `{}`",
        unwhitelist="Unwhitelisted `{}`",
        blacklist=Automodblacklist(
            add=AutomodBlacklistAdd(
                badargument="Word must be at least 3 characters long.",
                dupe="Can't add duplicate word",
                added="Added `{}` to the blacklist"
            ),
            remove=AutomodBlacklistRemove(
                doesntexist="You don't seem to be blacklisting that word",
                removed="Removed `{}` from the blacklist"
            ),
            display=AutomodBlacklistDisplay(
                doesntexist="No blacklisted words yet, use `{}blacklist add <word>` to get started",
                words="Blocked words"
            ),
            punishments=AutomodBlacklistPunishments(
                title="Warning punishments",
                description="The warning punishments for `{}` are `{}`.",
                set="Set punishment to `{}`"
            ),
            clear="Removed all blacklisted words"
        )
    ),
    autorole=Autorole(),
    chat=Chat(
        cog_description="Chat with Friday, say something on Friday's behalf, and more with the chat commands.",
        ratelimit=ChatRatelimit(
            title="You have sent me over `{count}` in that last `{human}` and are being rate limited, try again {stamp}",
            ads=ChatRatelimitAds(
                voting=ChatRatelimitAdsAd(
                    message="Get a higher message cap by voting on [Top.gg](https://top.gg/bot/476303446547365891/vote).",
                    button="Vote for more"
                ),
                streak="Get an even higher cap by keeping a voting streak of at least 2 days.",
                patron=ChatRatelimitAdsAd(
                    message="Get the most powerful message cap by becoming a [Patron](https://patreon.com/join/fridaybot).",
                    button="Become a Patron for more"
                )
            )
        ),
        flagged="My response was flagged and could not be sent, please try again",
        no_response="Somehow, I don't know what to say.",
        try_again_later="Something went wrong, please try again later",
        chat=ChatChat(
            command_name="chat",
            help="Talk or get info about chatting with Friday",
            commands=ChatChatCommands(
                talk=AppCommandDefault(
                    command_name="talk",
                    help="Chat with Friday, powered by GPT-3 and get a response.",
                    parameters=dict(
                        message=AppCommandParameterDefault(
                            name="message",
                            description="Your message to Friday"
                        )
                    )
                ),
                info=ChatCommandsInfo(
                    command_name="info",
                    help="Displays information about the current conversation",
                    no_history="No history found",
                    response_title="Chat Info",
                    response_field_titles=["Messages", "Voted messages", "Voting Streak messages", "Patroned messages", "Recent history resets", "Message History"],
                    response_rate="{rate} remaining"
                ),
                reset=AppCommandDefault(
                    command_name="reset",
                    help="Resets Friday's chat history. Helps if Friday is repeating messages"
                )
            )
        ),
        chatchannel=ChatChatchannel(
            command_name="chatchannel",
            help="Display or change the channel where the bot will chat",
            commands=dict(
                set=AppCommandDefault(
                    command_name="set",
                    help="Set the current channel so that I will always try to respond with something",
                    parameters=dict(
                        channel=AppCommandParameterDefault(
                            name="channel",
                            description="The channel that I will talk in"
                        )
                    )
                ),
                clear=AppCommandDefault(
                    command_name="clear",
                    help="Clear the current chat channel"
                )
            )
        ),
        persona=ChatPersona(
            command_name="persona",
            help="Change Friday's persona"
        )
    ),
    config=Config(
        cog_description="The general configuration commands for Friday",
        language=ConfigLanguage(
            invalid_lang="Language {language} does not exist, or is not supported."  # don't need this anymore
        ),
        userlanguage=ConfigUserLanguage(
            command_name="userlanguage",
            help="My language to speak with just you. Doesn't affect application commands",
            select_title="Select the language you would like me to speak",
            select_description="If you find something wrong with the translations, please contribute on the [Crowdin page](https://crwd.in/fridaybot)\n\nKeep in mind that this gets overridden with application commands by the locale set by a server and your client.",
            current_lang="Current language: `{current_language}`",
            new_lang="New language set to: `{new_language}`",
            new_lang_desc="Keep in mind that this gets overridden with application commands by the locale set by a server and your client."
        ),
        serverlanguage=ConfigServerLanguage(
            command_name="serverlanguage",
            help="My default language to speak in a server. Doesn't affect application commands",
            select_title="Select the language you would like me to speak",
            select_description="If you find something wrong with the translations, please contribute on the [Crowdin page](https://crwd.in/fridaybot)\n\nKeep in mind that this gets overridden with application commands by the locale set by a server and your client.",
            current_lang="Current language: `{current_language}`",
            new_lang="New language set to: `{new_language}`",
            new_lang_desc="Keep in mind that this gets overridden with application commands by the locale set by a server and your client."
        ),
        prefix=ConfigPrefix(
            help="Sets the prefix for Fridays commands",
            new_prefix="My new prefix is `{new_prefix}`",
            max_chars="Can't set a prefix with more than 5 characters"
        ),
        botchannel=ConfigBotChannel(
            help="The channel where bot commands live.",
            title="Bot Channel set"
        ),
        botchannelclear="Bot channel cleared",
        restrict=ConfigRestrict(
            help="Restricts the selected command to the bot channel. Ignored with manage server permission.",
            title="**{command_name}** has been restricted to the bot channel.",
            commands=ConfigRestrictCommands(
                list=ConfigRestrictList(
                  help="Lists the restricted commands",
                  response_title="Restricted Commands",
                  response_no_commands="No commands are restricted."
                )
            )
        ),
        unrestrict=ConfigUnrestrict(
            help="Unrestricts the selected command.",
            title="**{command_name}** has been unrestricted."
        ),
        enable=ConfigEnable(
            help="Enables the selected command(s).",
            title="**{command_name}** has been enabled."
        ),
        disable=ConfigDisable(
            help="Disable a command",
            title="**{command_name}** has been disabled."
        ),
        disablelist=ConfigDisableList(
            help="Lists all disabled commands.",
            title="Disabled Commands",
            none_found="There are no disabled commands."
        ),
        updates=ConfigUpdates(
            command_name="updates",
            help="Recieve updates on new features and changes for Friday",
            prompt="This channel is already subscribed to updates. Are you sure you want to subscribe again?",
            cancelled="Cancelled",
            reason="Called updates command, for Friday updates",
            followed="Updates channel followed",
            parameters=dict(
                channel=AppCommandParameterDefault(
                    name="channel",
                    description="The channel to get updates"
                )
            )
        )
    ),
    dbl=Dbl(),
    dice=Dice(
        cog_description="Roll some dice with advantage or just do some basic math.",
        dice=DiceDice(
            command_name="dice",
            help="Dugeons and Dragons dice rolling",
            response_title="Your total: {total}",
            response_description="Query: {query}\nResult: {result}",
            parameters=dict(
                roll=AppCommandParameterDefault(
                    name="roll",
                    description="The roll to be made. How to: https://d20.readthedocs.io/en/latest/start.html"
                )
            )
        )
    ),
    fun=Fun(),
    general=General(
        cog_description="Some general commands",
        invite=GeneralInvite(
            command_name="invite",
            help="Get the invite link to add me to your server"
        )
    ),
    help=Help(
        cog_description="If you would like to make a suggestion for a command please join the [Friday's Development](https://discord.gg/NTRuFjU) and explain your suggestion.\n\nFor more info on how commands work and how to format them please check out [docs.friday-bot.com](https://docs.friday-bot.com/).\n\n**Some commands will only show if you have the correct permissions to use them.**",
        no_help="No help found...",
        examples="Examples",
        signature="Signature",
        params="Available Parameters",
        commands="Commands",
        no_permissible_commands="No commands that you can use"
    ),
    issue=Issue(),
    log=Log(),
    nacl=Nacl(),
    dev=Dev(),
    ipc=Ipc(),
    topgg=Topgg(),
    logging=Logging(),
    modlogging=Modlogging(),
    meme=Meme(),
    database=Database(),
    datedevents=Datedevents(),
    sharding=Sharding(),
    stats=Stats(),
    scheduledevents=Scheduledevents(),
    moderation=Moderation(),
    music=Music(),
    patreons=Patreons(),
    api=Api(),
    stars=Stars(),
    choosegame=Choosegame(),
    ping=Ping(
        cog_description="Ping? Pong!",
        ping=PingPing(
            command_name="ping",
            help="Pong!",
            response_title="Pong!",
            response_description="⏳ API is {ping}ms"
        )
    ),
    redditlink=Redditlink(),
    reminder=Reminder(),
    support=Support(
        support=SupportSupport(
            command_name="support",
            help="Get an invite link to my support server"
        ),
        donate=SupportDonate(
            command_name="donate",
            help="Get the Patreon link for Friday"
        )
    ),
    welcome=Welcome(),
)

with open("./i18n/locales/en/commands.json", "w") as f:
  f.write(json.dumps(en, indent=2, ensure_ascii=False))
