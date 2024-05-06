from __future__ import annotations

import asyncio
import datetime
import functools
import json
import logging
import os
from collections import Counter, defaultdict
from typing import (TYPE_CHECKING, ClassVar, List, Literal, Optional,
                    TypedDict, Union)

import asyncpg
import discord
from openai import AsyncOpenAI
import validators
from discord import app_commands
from discord.app_commands.checks import Cooldown
from discord.ext import commands
from slugify import slugify

from cogs.log import CustomWebhook
from functions import MessageColors, MyContext, cache, config, embed, formats
from functions.config import ChatSpamConfig, PremiumPerks, PremiumTiersNew
from functions.time import format_dt, human_timedelta

if TYPE_CHECKING:
  from functions.custom_contexts import GuildContext
  from index import Friday

GuildMessageableChannel = Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread]

log = logging.getLogger(__name__)

POSSIBLE_SENSITIVE_MESSAGE = "*Possibly sensitive:* ||"
POSSIBLE_OFFENSIVE_MESSAGE = "**I failed to respond because my message might have been offensive, please choose another topic or try again**"

PERSONAS = [("🥰", "default", "Fridays default persona"), ("🏴‍☠️", "pirate", "Friday becomes one with the sea"), ("🍙", "kinyoubi", "Friday becomes one with the anime"), ("🇬🇧", "british", "Friday becomes British"), ("📝", "custom", "Make your own (premium only)")]

logging.getLogger("openai").setLevel(logging.WARNING)


class ChatError(commands.CheckFailure):
  pass


class ConfigChatChannel:
  def __init__(self, id: str, guild_id: str, webhook_url: Optional[str], persona: Optional[str] = None, persona_custom: Optional[str] = None):
    self.id = int(id, base=10)
    self.guild_id = int(guild_id, base=10)
    self.webhook_url = webhook_url
    self.persona = persona or "default"
    self.persona_custom = persona_custom

  async def get_or_fetch_channel(self, guild: discord.Guild) -> Optional[GuildMessageableChannel]:
    return guild.get_channel(self.id) or \
        await guild.fetch_channel(self.id)  # type: ignore

  def webhook(self, bot: Friday) -> Optional[discord.Webhook]:
    if self.webhook_url:
      return discord.Webhook.from_url(self.webhook_url, session=bot.session)


class Config:
  __slots__ = ("bot", "id", "chat_channels", "puser",)

  def __init__(self, *, record: asyncpg.Record, ccrecord: list[asyncpg.Record], bot: Friday):
    self.bot: Friday = bot
    self.id: int = int(record["id"], base=10)
    self.puser: Optional[int] = record["user_id"] if record else None
    self.chat_channels: list[ConfigChatChannel] = [ConfigChatChannel(**c) for c in ccrecord]

  def get_chat_channel(self, channel_id: int) -> Optional[ConfigChatChannel]:
    for c in self.chat_channels:
      if c.id == channel_id:
        return c


class UserConfig:
  __slots__ = ("bot", "user_id", "guild_ids",)

  def __init__(self, *, record: asyncpg.Record, bot: Friday):
    self.bot: Friday = bot
    self.user_id: int = int(record["user_id"], base=10)
    self.guild_ids: List[int] = record["guild_ids"] or []


class ContinueTokenLimit(discord.ui.View):
  def __init__(self, cog: Chat, ctx: MyContext, author_id: int, tier: PremiumTiersNew, persona: str, custom_persona: str | None, vote_streak_days: int):
    super().__init__(timeout=120.0)
    self.cog: Chat = cog
    self.message = None
    self.ctx: MyContext = ctx
    self.author_id: int = author_id
    self.tier: PremiumTiersNew = tier
    self.persona: str = persona
    self.custom_persona: str | None = custom_persona
    self.vote_streak_days: int = vote_streak_days
    self.remaining = 5
    self.button.label = f"Continue Response ({self.remaining}/5)"

  @discord.ui.button(label="Continue Response", custom_id="continue_response", style=discord.ButtonStyle.primary)
  async def button(self, interaction: discord.Interaction, button: discord.ui.Button):
    _, _, _ = self.cog._spam_check.is_spamming(self.ctx.message, self.tier, self.vote_streak_days)
    self.button.disabled = True
    self.button.label = "Loading..."
    await interaction.response.edit_message(view=self)
    assert interaction.message is not None
    response, response_reason, _ = await self.cog.openai_req(interaction.message, self.tier, self.persona, self.custom_persona, content=interaction.message.content, lang=self.ctx.lang_code, _continue=True)
    if response is not None and len(response) >= 2000:
      await interaction.response.edit_message(view=None)
      await interaction.response.send_message(content="This message has reached the maximum number of characters for a Discord message", ephemeral=True)
      self.stop()
      return
    await self.cog.chat_history[self.ctx.channel.id].update_last_bot_message(interaction.message.content + (response or ""))
    self.button.disabled = False
    self.remaining = self.remaining - 1
    self.button.label = f"Continue Response ({self.remaining}/5)"
    self.message = await interaction.edit_original_response(content=interaction.message.content + (response or ""), view=self if response_reason == "length" and not self.remaining <= 0 else None)
    # if self.remaining <= 0:
    #   if self.message:
    #     await self.message.edit(view=None)

    if response_reason != "length" or self.remaining <= 0:
      self.stop()

  async def on_timeout(self) -> None:
    if self.message:
      await self.message.edit(view=None)


class PersonaCustomModal(discord.ui.Modal, title='Custom Persona'):
  duration = discord.ui.TextInput(label='Persona', placeholder='Talk like an anime girl.', min_length=0, max_length=150)

  def __init__(self, cog: Chat) -> None:
    super().__init__()
    self.cog: Chat = cog

  async def on_submit(self, interaction: discord.Interaction) -> None:
    await interaction.response.defer()
    await self.cog.bot.pool.execute("UPDATE chatchannels SET persona_custom=$1 WHERE id=$2", self.duration.value, str(interaction.channel_id))
    self.cog.get_guild_config.invalidate(self.cog, interaction.guild_id)
    await interaction.edit_original_response(embed=embed(
        title=f"New Persona `Custom` set with the prompt `{self.duration.value}`"
    ), view=None)


class PersonaOptions(discord.ui.View):
  def __init__(self, cog: Chat, current: str, author_id: int, is_tiered: bool = False) -> None:
    super().__init__()
    self.cog: Chat = cog
    self.current: str = current.lower()
    self.author_id: int = author_id
    self.is_tiered: bool = is_tiered
    self.message: Optional[discord.Message] = None

    self.select.options = [discord.SelectOption(emoji=m[0], label=m[1].capitalize(), value=m[1], description=m[2], default=m[1].lower() == current.lower()) for m in PERSONAS]

    self.clear_items()
    self.add_item(self.select)
    if current.lower() == "custom" and is_tiered:
      self.add_item(self.custom)

  @discord.ui.select(
      custom_id="persona_select",
      options=[discord.SelectOption(label="Failed to load")],
      min_values=0, max_values=1)
  async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
    if not self.is_tiered and select.values[0].lower() == "custom":
      await interaction.response.send_message(embed=embed(title="This feature is only available to premium users", color=MessageColors.error()), ephemeral=True)
      return
    await self.cog.bot.pool.execute("UPDATE chatchannels SET persona=$1 WHERE id=$2", select.values[0], str(interaction.channel_id))
    self.cog.get_guild_config.invalidate(self.cog, interaction.guild_id)
    if select.values[0].lower() == "custom":
      await interaction.response.send_modal(PersonaCustomModal(self.cog))
      return
    try:
      if interaction.channel_id:
        self.cog.chat_history.pop(interaction.channel_id)
    except KeyError:
      pass
    await interaction.response.edit_message(embed=embed(title=f"New Persona `{select.values[0].capitalize()}`"), view=None)
    self.stop()

  @discord.ui.button(label="Custom", style=discord.ButtonStyle.primary, emoji="📝", custom_id="persona_custom")
  async def custom(self, interaction: discord.Interaction, button: discord.ui.Button):
    await interaction.response.send_modal(PersonaCustomModal(self.cog))

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if interaction.user and interaction.user.id == self.author_id:
      return True
    else:
      await interaction.response.send_message('This confirmation dialog is not for you.', ephemeral=True)
      return False

  async def on_timeout(self) -> None:
    if self.message:
      await self.message.delete()


class SpamChecker:
  def __init__(self):
    self.absolute_minute = commands.CooldownMapping.from_cooldown(ChatSpamConfig.absolute_minute_rate, 60, commands.BucketType.user)
    self.absolute_hour = commands.CooldownMapping.from_cooldown(ChatSpamConfig.absolute_hour_rate, 3600, commands.BucketType.user)
    self.free = commands.CooldownMapping.from_cooldown(ChatSpamConfig.free_rate, 43200, commands.BucketType.user)
    self.voted = commands.CooldownMapping.from_cooldown(ChatSpamConfig.voted_rate, 43200, commands.BucketType.user)
    self.streaked = commands.CooldownMapping.from_cooldown(ChatSpamConfig.streaked_rate, 43200, commands.BucketType.user)
    self.patron_1 = commands.CooldownMapping.from_cooldown(ChatSpamConfig.patron_1_rate, 43200, commands.BucketType.user)
    self.patron_2 = commands.CooldownMapping.from_cooldown(ChatSpamConfig.patron_2_rate, 43200, commands.BucketType.user)
    self.patron_3 = commands.CooldownMapping.from_cooldown(ChatSpamConfig.patron_3_rate, 43200, commands.BucketType.user)

  def is_spamming(self, msg: discord.Message, tier: PremiumTiersNew, vote_count: int) -> tuple[bool, Optional[Cooldown], Optional[Literal["free", "voted", "streaked", "patron_1", "patron_2", "patron_3"]]]:
    current = msg.created_at.timestamp()

    def define(mapping: commands.CooldownMapping) -> tuple[commands.Cooldown | None, float | None]:
      bucket = mapping.get_bucket(msg, current)
      return bucket, bucket and bucket.update_rate_limit(current)

    min_bucket, min_rate = define(self.absolute_minute)
    hour_bucket, hour_rate = define(self.absolute_hour)
    free_bucket, free_rate = define(self.free)
    voted_bucket, voted_rate = define(self.voted)
    streaked_bucket, streaked_rate = define(self.streaked)
    patron_1_bucket, patron_1_rate = define(self.patron_1)
    patron_2_bucket, patron_2_rate = define(self.patron_2)
    patron_3_bucket, patron_3_rate = define(self.patron_3)

    if min_rate:
      return True, min_bucket, None

    if hour_rate:
      return True, hour_bucket, None

    if free_rate and vote_count == 0 and tier == PremiumTiersNew.free:
      return True, free_bucket, "free"

    if voted_rate and 2 > vote_count > 0 and tier == PremiumTiersNew.voted:
      return True, voted_bucket, "voted"

    if streaked_rate and vote_count >= 2 and tier == PremiumTiersNew.streaked:
      return True, streaked_bucket, "streaked"

    if patron_1_rate and tier == PremiumTiersNew.tier_1:
      return True, patron_1_bucket, "patron_1"

    if patron_2_rate and tier == PremiumTiersNew.tier_2:
      return True, patron_2_bucket, "patron_2"

    if patron_3_rate and tier >= PremiumTiersNew.tier_3:
      return True, patron_3_bucket, "patron_3"

    return False, None, None


class ChatHistoryMessages(TypedDict):
  role: str  # Literal["user", "assistant", "system"]
  content: str


class ChatHistory:
  _limit: ClassVar[int] = 3
  _messages_per_group: ClassVar[int] = 2

  def __init__(self):
    self.lock = asyncio.Lock()
    self._history: list[ChatHistoryMessages] = []
    self._bot_name: str = "Friday"
    self.completion_tokens: int = 0
    self.prompt_tokens: int = 0
    self.total_tokens: int = 0

  def __repr__(self) -> str:
    return f"<Chathistory len={len(self.history())}>"

  def __str__(self) -> str:
    return "\n".join(str(m) for m in self.history())

  def __len__(self) -> int:
    return len("\n".join(str(m) for m in self.history()))

  def history(self, *, limit=_limit) -> list:
    return self._history[::-1][:limit * self._messages_per_group][::-1]

  def bot_repeating(self, *, limit=_limit) -> bool:
    bot_messages = [item for item in self.history(limit=limit) if item["role"] == "assistant"][::-1] or []
    repeats = [item for x, item in enumerate(bot_messages) if item == bot_messages[x - 1]]
    repeats = [*repeats, repeats[0]] if len(repeats) > 0 else repeats
    return bool(repeats and len(repeats) >= 3)

  def banned_nickname(self, name: str) -> str:
    banned = ["nigger", "nigg", "niger", "nig"]
    string = slugify(name).replace("-", "")
    for old, new in (("4", "a"), ("@", "a"), ("3", "e"), ("1", "i"), ("0", "o"), ("7", "t"), ("5", "s")):
      string = string.replace(old, new)
    return name if string.lower() not in banned else "Cat"

  async def messages(self, *, my_name: str = None, user_name: str = None, limit=_limit, tier: PremiumTiersNew = PremiumTiersNew.free, lang: str = "English", persona: str = None, persona_custom: str = None) -> list[ChatHistoryMessages]:
    bonus = "Talk like a friend."
    if persona == "pirate":
      bonus = "Talk like a pirate."
    elif persona == "kinyoubi":
      bonus = "Talk like an anime girl."
    elif persona == "british":
      bonus = "Talk like a british person."
    if tier >= PremiumTiersNew.tier_2:
      if persona == "custom":
        bonus = persona_custom
    # elif persona != "friday" and msg.guild:
    #   await self.bot.pool.execute("UPDATE servers SET persona=$1 WHERE id=$2", "friday", str(msg.guild.id))
    #   self.get_guild_config.invalidate(self, msg.guild.id)
    async with self.lock:
      while len(self._history) > limit * self._messages_per_group:
        self._history.pop(0)
      response: list[ChatHistoryMessages] = [
          {'role': 'system', 'content': f"You're '{my_name}'[female] a friendly & funny Discord chatbot made by 'Motostar'[male] and born on Aug 7, 2018. You'll respond in the users language."},
          # {'(Female Replacement Intelligent Digital Assistant Youth)' if my_name == 'friday' else ''}
      ]
      if bonus:
        response.append({'role': "system", "content": bonus})
      response.extend(self._history)
      return response

  async def add_message(self, msg: discord.Message, bot_content: str, *, user_content: str = None, user_name: str = None, bot_name: str = None):
    async with self.lock:
      user_content = user_content or msg.clean_content
      user_name = user_name or msg.author.display_name
      self._bot_name = bot_name = bot_name or msg.guild and msg.guild.me.display_name or "Friday"
      self._history.append({"role": "user", "content": f"{user_content}"})
      self._history.append({"role": "assistant", "content": f"{bot_content}"})

  async def update_last_bot_message(self, new_content: str):
    async with self.lock:
      bot_message_index = self._history.index([msg for msg in self._history if msg.get("role") == "assistant"][-1])
      log.info(self._history[bot_message_index]["content"])
      self._history[bot_message_index]["content"] = new_content


class CooldownByRepeating(commands.CooldownMapping):
  def _bucket_key(self, msg: discord.Message):
    return (msg.content)


class Chat(commands.Cog):
  """Chat with Friday, say something on Friday's behalf, and more with the chat commands."""

  def __init__(self, bot: Friday):
    self.bot: Friday = bot
    self.openai = AsyncOpenAI(api_key=os.environ["OPENAI"])

    # https://help.openai.com/en/articles/5008629-can-i-use-concurrent-api-calls
    self.api_lock = asyncio.Semaphore(2)  # bot.openai_api_lock

    self._spam_check = SpamChecker()
    self._repeating_spam = CooldownByRepeating.from_cooldown(3, 60 * 3, commands.BucketType.channel)

    # channel_id: list
    self.chat_history: defaultdict[int, ChatHistory] = defaultdict(lambda: ChatHistory())

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  @cache.cache()
  async def get_guild_config(self, guild_id: int) -> Optional[Config]:
    query = """SELECT *
    FROM servers s
    LEFT OUTER JOIN patrons p
      ON s.id = ANY(p.guild_ids)
    WHERE s.id=$1"""
    ccquery = """SELECT *
    FROM chatchannels
    WHERE guild_id=$1"""
    conn = self.bot.pool
    try:
      record = await conn.fetchrow(query, str(guild_id))
      ccrecord = await conn.fetch(ccquery, str(guild_id))
    except Exception as e:
      raise e
    else:
      log.debug(f"PostgreSQL Query: \"{query}\" + {str(guild_id)}\n\"{ccquery}\"")
      if record is not None:
        return Config(record=record, ccrecord=ccrecord, bot=self.bot)
    return None

  @commands.Cog.listener()
  async def on_invalidate_patreon(self, guild_id: int):
    self.get_guild_config.invalidate(self, guild_id)

  @discord.utils.cached_property
  def webhook(self) -> CustomWebhook:
    """Returns the webhook for logging chat messages to Discord."""
    return CustomWebhook.partial(os.environ.get("WEBHOOKCHATID"), os.environ.get("WEBHOOKCHATTOKEN"), session=self.bot.session)  # type: ignore

  @commands.command(name="say", aliases=["repeat"], help="Make Friday say what ever you want")
  async def say(self, ctx: MyContext, *, content: str):
    if content in ("im stupid", "i'm stupid", "i am dumb", "im dumb"):
      return await ctx.reply("yeah we know", allowed_mentions=discord.AllowedMentions.none())
    await ctx.reply(content, allowed_mentions=discord.AllowedMentions.none())

  @commands.command(name="silentsay", aliases=["saysilent"])
  @commands.bot_has_permissions(manage_messages=True)
  async def silent_say(self, ctx: MyContext, *, content: str):
    if content in ("im stupid", "i'm stupid", "i am dumb", "im dumb"):
      return await ctx.reply("yeah we know", allowed_mentions=discord.AllowedMentions.none())
    await ctx.message.delete()
    await ctx.send(content, allowed_mentions=discord.AllowedMentions.none())

  @commands.hybrid_group("chat", fallback="talk", invoke_without_command=True, case_insensitive=True)
  @app_commands.describe(message="Your message to Friday")
  async def chat(self, ctx: MyContext, *, message: str):
    """Chat with Friday, powered by ChatGPT and get a response."""
    try:
      await self.chat_message(ctx, content=message)
    except ChatError as e:
      await ctx.send(embed=embed(title=str(e), color=MessageColors.error()))

  @chat.command("info")
  async def chat_info(self, ctx: MyContext):
    """Displays information about the current conversation."""
    current = ctx.message.created_at.timestamp()

    def get_tokens(_type: commands.CooldownMapping):
      r = _type.get_bucket(ctx.message, current)
      return r and r.get_tokens(ctx.message.created_at.timestamp())
    free_rate = get_tokens(self._spam_check.free)
    voted_rate = get_tokens(self._spam_check.voted)
    streaked_rate = get_tokens(self._spam_check.streaked)
    patroned_1_rate = get_tokens(self._spam_check.patron_1)
    patroned_2_rate = get_tokens(self._spam_check.patron_2)
    patroned_3_rate = get_tokens(self._spam_check.patron_3)
    history = self.chat_history[ctx.channel.id]
    content = history and str(history) or ctx.lang["chat"]["chat"]["commands"]["info"]["no_history"]
    rate_message = ctx.lang.chat.chat.commands.info.response_rate
    await ctx.send(embed=embed(
        title=ctx.lang["chat"]["chat"]["commands"]["info"]["response_title"],
        fieldstitle=ctx.lang["chat"]["chat"]["commands"]["info"]["response_field_titles"],
        fieldsval=[
            rate_message.format(rate=free_rate), rate_message.format(rate=voted_rate), rate_message.format(rate=streaked_rate), rate_message.format(rate=patroned_1_rate), rate_message.format(rate=patroned_2_rate), rate_message.format(rate=patroned_3_rate), str(self.bot.chat_repeat_counter[ctx.channel.id]), f"```\n{content}\n```"],
        fieldsin=[True, True, True, True, True, True, False, False]
    ))

  @chat.command("reset")
  async def chat_reset_history(self, ctx: MyContext):
    """Resets Friday's chat history. Helps if Friday is repeating messages"""
    await self.reset_history(ctx)

  @commands.command(name="reset")
  async def reset_history(self, ctx: MyContext):
    """Resets Friday's chat history. Helps if Friday is repeating messages"""
    try:
      self.chat_history.pop(ctx.channel.id)
    except KeyError:
      await ctx.send(embed=embed(title="No history to delete"))
    except Exception as e:
      raise e
    else:
      self.bot.chat_repeat_counter[ctx.channel.id] += 1
      await ctx.send(embed=embed(title="My chat history has been reset", description="I have forgotten the last few messages"))

  async def create_chatchannel(self, ctx: GuildContext, channel: GuildMessageableChannel) -> None:
    assert self.bot.patreon is not None
    current_tier = PremiumTiersNew.free
    patrons = await self.bot.patreon.get_patrons()

    patron = next((p for p in patrons if p.id == ctx.author.id), None)

    if patron is not None:
      current_tier = PremiumTiersNew(patron.tier) if patron.tier > current_tier.value else current_tier

    current_chat_channel_ids: list[str] = await ctx.db.fetch("SELECT id FROM chatchannels WHERE guild_id=$1", str(ctx.guild.id))
    if len(current_chat_channel_ids) >= config.PremiumPerks(current_tier).max_chat_channels:
      await ctx.send(embed=embed(title="You have reached the maximum amount of chat channels you can have", color=MessageColors.error()))
      return

    await ctx.db.execute("INSERT INTO chatchannels (id,guild_id) VALUES($1,$2) ON CONFLICT DO NOTHING", str(channel.id), str(ctx.guild.id))
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.send(embed=embed(title="Chat channel set", description=f"I will now respond to every message in this channel\n{channel.mention}"))

  @commands.hybrid_group(name="chatchannel", fallback="add", extras={"examples": ["#channel"]}, invoke_without_command=True, case_insensitive=True)
  @commands.guild_only()
  @commands.has_permissions(manage_channels=True)
  async def chatchannel(self, ctx: GuildContext, channel: GuildMessageableChannel):
    """Set the current channel so that I will always try to respond with something"""
    await self.create_chatchannel(ctx, channel)

  @chatchannel.command("webhook", extras={"examples": {"#chatbot 1", "#chatbot 0", "#chatchannel false", "#chatchannel true"}})
  @commands.guild_only()
  @commands.has_permissions(manage_channels=True)
  @commands.bot_has_permissions(manage_webhooks=True)
  async def chatchannel_webhook(self, ctx: GuildContext, channel: GuildMessageableChannel, enable: bool = None):
    """Toggles webhook chatting with Friday in the current chat channel"""

    config = await self.get_guild_config(ctx.guild.id)
    c = config and config.get_chat_channel(channel.id)
    if config is None or c is None:
      prompt = await ctx.prompt("This channel has not been set as a chatchannel yet. Would you like to set it as a chatchannel now?", timeout=30)
      if prompt is not True:
        return
      await self.create_chatchannel(ctx, channel)
      config = await self.get_guild_config(ctx.guild.id)
      c = config and config.get_chat_channel(channel.id)
      assert c is not None

      if enable is None:
        return await ctx.edit(embed=embed(title=f"The current chat channel's webhook mode is set to {bool(c and c.webhook_url is not None)}"))

      webhook = None
      if enable is True and c.webhook(self.bot) is None:
        try:
          avatar = await self.bot.user.avatar.read() if self.bot.user.avatar else None
          webhook = await config.chat_channel.create_webhook(name=self.bot.user.display_name, avatar=avatar)  # type: ignore
        except Exception:
          return await ctx.edit(embed=embed(title="Looks like I can't make webhooks on that channel", color=MessageColors.red()))
      await ctx.db.execute("UPDATE chatchannels SET webhook_url=$1 WHERE id=$2", webhook and webhook.url, str(channel.id))
      self.get_guild_config.invalidate(self, ctx.guild.id)
      await ctx.edit(embed=embed(title=f"Webhook mode is now {enable}"))
      return
    if enable is None:
      return await ctx.send(embed=embed(title=f"The current chat channel's webhook mode is set to {bool(c and c.webhook_url is not None)}"))

    webhook = None
    if enable is True and c.webhook(self.bot) is None:
      try:
        avatar = await self.bot.user.avatar.read() if self.bot.user.avatar else None
        webhook = await config.chat_channel.create_webhook(name=self.bot.user.display_name, avatar=avatar)  # type: ignore
      except Exception:
        return await ctx.send(embed=embed(title="Looks like I can't make webhooks on that channel", color=MessageColors.red()))
    await ctx.db.execute("UPDATE chatchannels SET webhook_url=$1 WHERE id=$2", webhook and webhook.url, str(channel.id))
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.send(embed=embed(title=f"Webhook mode is now {enable}"))

  @chatchannel.command(name="remove")
  @commands.guild_only()
  @commands.has_permissions(manage_channels=True)
  async def chatchannel_remove(self, ctx: GuildContext, channel: GuildMessageableChannel):
    """Removes a chat channel"""
    await ctx.db.execute("DELETE FROM chatchannels WHERE id=$1 AND guild_id=$2;", str(channel.id), str(ctx.guild.id))
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.send(embed=embed(title="Chat channel removed", description="I will no longer respond to messages in this channel"))

  @chatchannel.command(name="list")
  @commands.guild_only()
  async def chatchannel_list(self, ctx: GuildContext):
    """Lists the channels that Friday will always try to respond with something"""
    channel_ids: list[asyncpg.Record] = await ctx.db.fetch("SELECT id FROM chatchannels WHERE guild_id=$1", str(ctx.guild.id))
    if channel_ids is None:
      return await ctx.send(embed=embed(title="No chat channels set"))
    await ctx.send(embed=embed(title="Chat channels", description="\n".join([f"<#{channel_id['id']}>" for channel_id in channel_ids])))

  @chatchannel.command(name="clear")
  @commands.guild_only()
  @commands.has_permissions(manage_channels=True)
  async def chatchannel_clear(self, ctx: GuildContext):
    """Clear the current chat channel"""
    await ctx.db.execute("DELETE FROM chatchannels WHERE guild_id=$1;", str(ctx.guild.id))
    self.get_guild_config.invalidate(self, ctx.guild.id)
    await ctx.send(embed=embed(title="Chat channel cleared", description="I will no longer respond to messages in this channel"))

  @chatchannel.command(name="persona")
  @commands.guild_only()
  @commands.has_permissions(manage_channels=True)
  async def chatchannel_persona(self, ctx: GuildContext, channel: GuildMessageableChannel):
    """Change Friday's persona for a chat channel"""
    config = await self.get_guild_config(ctx.guild.id)
    c = config and config.get_chat_channel(channel.id)
    if self.bot.patreon is None:
      return await ctx.send(embed=embed(title="This command is not available right now, please contact the developer on the support server", color=MessageColors.error()))
    current_tier = await self.bot.patreon.fetch_current_tier(ctx)
    if config is None or c is None:
      prompt = await ctx.prompt("This channel has not been set as a chatchannel yet. Would you like to set it as a chatchannel now?", timeout=30)
      if prompt is not True:
        return
      await self.create_chatchannel(ctx, channel)
      config = await self.get_guild_config(ctx.guild.id)
      c = config and config.get_chat_channel(channel.id)
      assert c is not None
      view = PersonaOptions(self, c.persona, ctx.author.id, bool(current_tier >= PremiumTiersNew.tier_2))
      view.message = await ctx.edit(view=view, embed=None, content=None)
      return
    view = PersonaOptions(self, c.persona, ctx.author.id, bool(current_tier >= PremiumTiersNew.tier_2))
    view.message = await ctx.send(view=view)

  @commands.hybrid_command(name="persona", with_app_command=False, hidden=True)
  @commands.guild_only()
  @commands.has_permissions(manage_channels=True)
  async def persona(self, ctx: GuildContext):
    """Change Friday's persona"""
    await ctx.send(embed=embed(title="This command has been moved to `/chatchannel persona`", colour=MessageColors.error()), ephemeral=True)

  @cache.cache()
  async def content_filter_flagged(self, text: str) -> tuple[bool, list[str]]:
    if self.bot.testing:
      return False, []
    async with self.api_lock:
      response = await self.openai.moderations.create(
                  model="text-moderation-latest",
                  input=text,
              )
    if response is None:
      return False, []
    response = response.results[0]
    categories = [name for name, value in response.categories if value == 1]
    return bool(response.flagged == 1), categories

  async def openai_req(
      self,
      msg: discord.Message,
      current_tier: PremiumTiersNew,
      persona: str = None,
      persona_custom: str = None,
      *,
      content: str = None,
      lang: str = "English",
      _continue: bool = False,
  ) -> tuple[Optional[str], Optional[Literal["stop", "length", "function_call"]], Optional[dict]]:
    content = content or msg.clean_content
    author_prompt_name = msg.author.display_name
    my_prompt_name = msg.guild.me.display_name if msg.guild else self.bot.user.name

    messages = await self.chat_history[msg.channel.id].messages(my_name=my_prompt_name, user_name=author_prompt_name, tier=current_tier, lang=lang, persona=persona, persona_custom=persona_custom)
    async with self.api_lock:
      if _continue:
        log.info(messages)
        response = await self.openai.chat.completions.create(model=PremiumPerks(current_tier).model,
        messages=messages,
        temperature=0,
        max_tokens=PremiumPerks(current_tier).max_chat_tokens,
        user=str(msg.channel.id))
      else:
        log.info(messages + [{'role': 'user', 'content': f"{content}"}])
        response = await self.openai.chat.completions.create(model=PremiumPerks(current_tier).model,
        messages=messages + [{'role': 'user', 'content': f"{content}"}],
        max_tokens=PremiumPerks(current_tier).max_chat_tokens,
        user=str(msg.channel.id))
    if response is None:
      return None, None, None
    self.chat_history[msg.channel.id].completion_tokens = response.usage.completion_tokens  # type: ignore
    self.chat_history[msg.channel.id].prompt_tokens = response.usage.prompt_tokens  # type: ignore
    self.chat_history[msg.channel.id].total_tokens = response.usage.total_tokens  # type: ignore
    final_message = response.choices[0].message.content
    return final_message, response.choices[0].finish_reason, response.choices[0].message.function_call   # type: ignore

  @commands.Cog.listener()
  async def on_message(self, msg: discord.Message):
    await self.bot.wait_until_ready()

    if msg.author.bot and msg.author.id != 892865928520413245:
      return

    if msg.clean_content == "" or msg.activity is not None:
      return

    if msg.clean_content.lower().startswith(tuple(self.bot.log.get_prefixes())):
      return

    if not hasattr(msg.type, "name") or (msg.type.name != "default" and msg.type.name != "reply"):
      return

    if msg.author.id in self.bot.blacklist:
      return

    if msg.guild is not None and msg.guild.id in self.bot.blacklist:
      return

    ctx = await self.bot.get_context(msg, cls=MyContext)
    if ctx.command is not None or msg.webhook_id is not None:
      return

    if not ctx.bot_permissions.send_messages:
      return

    valid = validators.url(msg.clean_content)  # type: ignore
    if valid:
      return

    try:
      # await self.answer_message(msg)
      await self.chat_message(ctx)
    except ChatError:
      pass

  async def chat_message(self, ctx: MyContext | GuildContext, *, content: str = None) -> None:
    msg = ctx.message
    content = content or msg.clean_content
    current_tier: PremiumTiersNew = PremiumTiersNew.free

    config = None
    webhook = None
    chat_channel = None
    if ctx.guild:
      if self.bot.log and not ctx.interaction:
        conf = await self.bot.log.get_guild_config(ctx.guild.id)
        if not conf:
          await ctx.db.execute(f"INSERT INTO servers (id) VALUES ({str(ctx.guild.id)}) ON CONFLICT DO NOTHING")
          self.bot.log.get_guild_config.invalidate(self.bot.log, ctx.guild.id)
          self.get_guild_config.invalidate(self, ctx.guild.id)
          conf = await self.bot.log.get_guild_config(ctx.guild.id)
        if "chat" in conf.disabled_commands:
          return

      config: Optional[Config] = await self.get_guild_config(ctx.guild.id)
      if config is None:
        log.error(f"Config was not available in chat for (guild: {ctx.guild.id if ctx.guild else None}) (channel type: {ctx.channel.type if ctx.channel else 'uhm'}) (user: {msg.author.id})")
        raise ChatError("Guild config not available, please contact developer.")

      chat_channel = config.get_chat_channel(ctx.channel.id)
      if not ctx.command:
        chat_channel_channel = chat_channel and await chat_channel.get_or_fetch_channel(ctx.guild)
        if chat_channel_channel is not None and ctx.channel != chat_channel_channel:
          if ctx.guild.me not in msg.mentions:
            return
        elif chat_channel_channel is None and ctx.guild.me not in msg.mentions:
          return

      if chat_channel is not None:
        try:
          webhook = chat_channel.webhook(self.bot)
        except discord.NotFound:
          await self.bot.pool.execute("""UPDATE chatchannels SET webhook_url=NULL WHERE id=$1;""", str(chat_channel.id))
          self.get_guild_config.invalidate(self, config.id)
          log.info(f"{config.id} deleted their webhook chatchannel without disabling it first")
          try:
            await ctx.send(embed=embed(title="Failed to find webhook, please asign a new one", color=MessageColors.ERROR), ephemeral=True)
            return
          except BaseException as e:
            log.error(e)
            return

    assert self.bot.patreon is not None
    current_tier = await self.bot.patreon.fetch_current_tier(ctx)

    char_count = len(content)
    max_content = PremiumPerks(PremiumTiersNew(current_tier)).max_chat_characters
    if char_count > max_content:
      raise ChatError(f"Message is too long. Max length is {max_content} characters.")

    dbl = self.bot.dbl
    vote_streak = dbl and await dbl.user_streak(ctx.author.id)

    # Anything to do with sending messages needs to be below the above check
    response = None
    is_spamming, rate_limiter, rate_name = self._spam_check.is_spamming(msg, current_tier, vote_streak and vote_streak.days or 0)
    if is_spamming and rate_limiter:
      if not ctx.bot_permissions.embed_links:
        return
      retry_after = ctx.message.created_at + datetime.timedelta(seconds=rate_limiter.get_retry_after())

      log.info(f"{msg.author} ({msg.author.id}) is being ratelimited at over {rate_limiter.rate} messages and can retry after {human_timedelta(retry_after, source=ctx.message.created_at, accuracy=2, brief=True)}")

      ad_message = ""
      view = discord.ui.View()
      if rate_name and not current_tier >= PremiumTiersNew.tier_1:
        if not rate_name == "streaked":
          if not rate_name == "voted":
            ad_message += ctx.lang.chat.ratelimit.ads.voting.message + "\n"
          ad_message += ctx.lang.chat.ratelimit.ads.streak + "\n"
          view.add_item(discord.ui.Button(label=ctx.lang.chat.ratelimit.ads.voting.button, url="https://top.gg/bot/476303446547365891/vote"))
        ad_message += ctx.lang.chat.ratelimit.ads.patron.message
        view.add_item(discord.ui.Button(label=ctx.lang.chat.ratelimit.ads.patron.button, url="https://patreon.com/join/fridaybot"))
      now = discord.utils.utcnow()
      retry_dt = now + datetime.timedelta(seconds=rate_limiter.per)
      await ctx.reply(embed=embed(title=ctx.lang.chat.ratelimit.title.format(count=f"{formats.plural(rate_limiter.rate):message}", human=human_timedelta(retry_dt, source=now, accuracy=2), stamp=format_dt(retry_after, style='R')), description=ad_message, color=MessageColors.error()), view=view, webhook=webhook, mention_author=False)
      return
    chat_history = self.chat_history[msg.channel.id]
    async with ctx.typing():
      try:
        response, response_reason, response_function_call = await self.openai_req(msg, current_tier, chat_channel and chat_channel.persona, chat_channel and chat_channel.persona_custom, content=content, lang=ctx.lang_code)
      except Exception as e:
        # resp = await ctx.send(embed=embed(title="", color=MessageColors.error()))
        self.bot.dispatch("chat_completion", msg, True, filtered=None, messages=self.chat_history[msg.channel.id].history(limit=PremiumPerks(current_tier).max_chat_history),)
        log.error(f"OpenAI error: {e}")
        await ctx.reply(embed=embed(title=ctx.lang.chat.try_again_later, colour=MessageColors.error()), webhook=webhook, mention_author=False)
        return
      if response_reason != "function_call":
        if response is None or response == "":
          raise ChatError(ctx.lang.chat.no_response)
        await chat_history.add_message(msg, response, user_content=content)
        flagged, flagged_categories = await self.content_filter_flagged(response)

    if not flagged:
      await ctx.reply(content=response, allowed_mentions=discord.AllowedMentions.none(), webhook=webhook, mention_author=False) 
      log.info(f"{PremiumTiersNew(current_tier)}[{msg.guild and chat_channel and chat_channel.persona}] - [{ctx.lang_code}] [{ctx.author.name}] {content}  [Me] {response}")
      await self.webhook.safe_send(username=self.bot.user.name, avatar_url=self.bot.user.display_avatar.url, content=f"{PremiumTiersNew(current_tier)} - **{ctx.author.name}:** {content}\n**Me:** {response}")
    else:
      await ctx.reply(f"**{ctx.lang.chat.flagged}**", webhook=webhook, mention_author=False)
      log.info(f"{PremiumTiersNew(current_tier)}[{msg.guild and chat_channel and chat_channel.persona}] - [{ctx.lang_code}] [{ctx.author.name}] {content}  [Me] Flagged message: \"{response}\" {formats.human_join(flagged_categories, final='and')}")
      await self.webhook.safe_send(username=self.bot.user.name, avatar_url=self.bot.user.display_avatar.url, content=f"{PremiumTiersNew(current_tier)} - **{ctx.author.name}:** {content}\n**Me:** Flagged message: {response} {flagged_categories}")
    self.bot.dispatch(
        "chat_completion",
        msg,
        False,
        filtered=int(flagged),
        persona=msg.guild and chat_channel and chat_channel.persona,
        messages=self.chat_history[msg.channel.id].history(limit=PremiumPerks(current_tier).max_chat_history),
        prompt_tokens=self.chat_history[msg.channel.id].prompt_tokens,
        completion_tokens=self.chat_history[msg.channel.id].completion_tokens,
        total_tokens=self.chat_history[msg.channel.id].total_tokens)

    async with chat_history.lock:
      if chat_history.bot_repeating():
        self.chat_history.pop(ctx.channel.id)
        self.bot.chat_repeat_counter[msg.channel.id] += 1
        log.info("Popped chat history for channel #{}".format(ctx.channel))


async def setup(bot):
  if not hasattr(bot, "cluster"):
    bot.cluster = None

  if not hasattr(bot, "chat_repeat_counter"):
    bot.chat_repeat_counter = Counter()

  await bot.add_cog(Chat(bot))
