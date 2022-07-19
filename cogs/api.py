from __future__ import annotations

import datetime
import logging
# import hmac
# import json
import os
import ssl
from typing import (TYPE_CHECKING, Any, List, Optional, Protocol, TypedDict,
                    Union)

import aiohttp_cors
import asyncpg
import discord
from aiohttp import web
from discord.ext import commands

# from functions import config

if TYPE_CHECKING:
  from cogs.automod import AutoMod
  from cogs.automod import Config as AutoModConfig
  from cogs.automod import SpamType
  from cogs.chat import Chat
  from cogs.chat import Config as ChatConfig
  from cogs.general import General
  from cogs.log import Config as LogConfig
  from cogs.log import Log
  from cogs.logging import ModConfig as LoggingConfig
  from cogs.logging import ModLogging
  # from cogs.patreons import Patreons
  from cogs.redditlink import Config as RedditLinkConfig
  from cogs.redditlink import redditlink
  from cogs.welcome import Config as WelcomeConfig
  from cogs.welcome import Welcome
  from index import Friday

  class StatsClusterType(TypedDict):
    guilds: int
    ready: bool
    connected: dict[int, bool]
    latencies: dict[int, float]
    uptime: int

  class StatsType(TypedDict):
    shard_count: int
    clusters: List[StatsClusterType]

  class GetGuildType(TypedDict):
    prefix: str
    chatchannel: Optional[int]
    lang: Optional[str]
    persona: Optional[str]
    name: str
    tier: int
    icon: Optional[str]
    reddit_extract: bool
    channels: list[Any]

  class GetModerationType(TypedDict):
    remove_invites: Optional[bool]
    max_mentions: Optional[SpamType]
    max_messages: Optional[SpamType]
    max_content: Optional[SpamType]
    channels: list[dict]
    top_role: dict
    roles: list[dict]
    tier: int
    mute_role: Optional[str]
    whitelist: Optional[list[str]]
    mod_log_events: Optional[list[str]]
    mod_log_channel_id: Optional[int]
    welcome: Optional[dict]
    blacklist: Optional[dict]

  class GetMusicType(TypedDict):
    customsounds: list[dict]
    tier: int

  class GetCommandsType(TypedDict):
    channels: list
    cogs: list
    config: dict

log = logging.getLogger(__name__)


class CogConfig(Protocol):
  async def get_guild_config(self, guild_id: int, *, connection: Optional[Union[asyncpg.Pool, asyncpg.Connection]] = None):
    ...


class HTTPImATeaPot(web.HTTPClientError):
  "This is by far the best error code"
  status_code = 418

  @property
  def reason(self) -> str:
    return self._reason or "I'm a teapot"


class HTTPBlocked(web.HTTPClientError):
  status_code = 403

  @property
  def reason(self) -> str:
    return self._reason or "You have been blocked from using this Service"


class API(commands.Cog):
  def __init__(self, bot: Friday):
    self.app = web.Application(logger=log)
    self.site = None
    self.bot: Friday = bot

    # TODO: Not sure how to choose which cluster to ping from API
    # Use something like port 4001 when clusters
    # But now there is ssl so idk what i will do when clusters lmao
    if self.bot.canary or self.bot.prod:
      self.port = 443  # + bot.cluster_idx
    else:
      self.port = 4001

  def __repr__(self) -> str:
    return f"<cogs.{self.__cog_name__}>"

  async def cog_load(self):
    self.bot.loop.create_task(self.run(), name="Web")

  async def cog_unload(self):
    self.bot.loop.create_task(self.runner.cleanup())

  async def get_guild_config(self, cog_name: str, guild_id: int) -> Any:
    cog: CogConfig = self.bot.get_cog(cog_name)  # type: ignore
    if cog is None:
      return None
    return await cog.get_guild_config(guild_id)

  async def run(self):  # noqa: C901
    app = self.app
    bot = self.bot
    # TODO: Add CORS support https://github.com/aio-libs/aiohttp-cors  allow_origin=["https://friday-bot.com"], allow_methods=["GET"]
    cors = aiohttp_cors.setup(app, defaults={
        "http://localhost:3000": aiohttp_cors.ResourceOptions(),
        "https://friday-bot.com": aiohttp_cors.ResourceOptions(allow_headers="*", allow_credentials=True)
    })
    routes = web.RouteTableDef()

    # Adds too much complexity to the API
    # also don't think this needs to be private
    # @app.before_request
    # def before_request():
    #   if request.headers.get("Authorization") != os.environ.get("APIREQUESTS"):
    #     return abort(401)

    @routes.get("/")
    async def index(request: web.Request) -> web.Response:
      response = web.HTTPSeeOther("https://youtu.be/dQw4w9WgXcQ")
      response.headers["Cache-Control"] = "no-cache, no-store, max-age=0, must-revalidate"
      response.headers["Pragma"] = "no-cache"
      response.headers["Expires"] = "Mon, 01 Jan 1990 00:00:00 GMT"
      return response

    @routes.get("/stats")
    async def stats(request: web.Request) -> web.Response:
      response: StatsType = {
          "shard_count": len(bot.shards),
          "clusters": [
              {
                  "guilds": len(bot.guilds),
                  "ready": bot.is_ready(),
                  "connected": {
                      i.id: not i.is_closed()
                      for i in bot.shards.values()
                  },
                  "latencies": {
                      i.id: i.latency
                      for i in bot.shards.values()
                  },
                  "uptime": int((datetime.datetime.utcnow() - self.bot.uptime).total_seconds())
              }
          ],
      }
      return web.json_response(response)

    @routes.get("/invite")
    async def get_invite(request: web.Request) -> web.Response:
      invite: Optional[General] = bot.get_cog("General")  # type: ignore
      if invite is None:
        return web.HTTPInternalServerError()

      response = web.HTTPMovedPermanently(invite.link)
      response.headers["Cache-Control"] = "no-cache, no-store, max-age=0, must-revalidate"
      response.headers["Pragma"] = "no-cache"
      response.headers["Expires"] = "Mon, 01 Jan 1990 00:00:00 GMT"
      return response

    @routes.get("/guilds")
    async def get_guilds(request: web.Request) -> web.Response:
      if "guilds" not in request.headers:
        return HTTPImATeaPot()
      if len(request.headers["guilds"]) == 0:
        return HTTPImATeaPot()

      guild_ids = [int(i, base=10) for i in request.headers["guilds"].split(",")]
      guilds = []
      for guild_id in guild_ids:
        try:
          guild = bot.get_guild(guild_id)
          if guild is None:
            await bot.fetch_guild(guild_id)
        except discord.Forbidden:
          continue
        if guild is not None and guild.id not in self.bot.blacklist:
          guilds.append(guild)
      if len(guilds) == 0:
        return web.json_response([])
      guilds = [dict(id=str(i.id)) for i in guilds]
      return web.json_response(guilds)

    @routes.get("/guilds/{gid}")
    async def get_guild(request: web.Request) -> web.Response:
      gid = request.match_info["gid"]
      guild = bot.get_guild(int(gid, base=10))
      if guild is None:
        try:
          guild = await bot.fetch_guild(int(gid, base=10))
          if guild is None:
            return web.HTTPNotFound(reason="Guild not found")
        except Exception as e:
          return web.HTTPNotFound(reason=f"Guild not found: {e}")
      elif guild.unavailable:
        return web.HTTPBadGateway(reason="Guild is unavailable")

      if gid in self.bot.blacklist:
        return HTTPBlocked(reason="This server is blacklisted from the bot.")

      channels = [{
          "name": i.name,
          "id": str(i.id),
          "type": str(i.type),
          "position": i.position,
          "parent_id": i.category.id if i.category is not None else None,
      } for i in guild.channels if i.type in (discord.ChannelType.text, discord.ChannelType.category)]

      chat_cog: Optional[Chat] = self.bot.get_cog("Chat")  # type: ignore
      chat_config: Optional[ChatConfig] = chat_cog and await chat_cog.get_guild_config(int(gid, base=10))
      reddit_cog: Optional[redditlink] = self.bot.get_cog("redditlink")  # type: ignore
      reddit_config: Optional[RedditLinkConfig] = reddit_cog and await reddit_cog.get_guild_config(int(gid, base=10))
      # reddit_extract = await self.bot.db.query("SELECT reddit_extract FROM servers WHERE id=$1 LIMIT 1", str(gid))

      lang_code = self.bot.languages.get(guild.id, "en")

      response: GetGuildType = {
          "prefix": bot.prefixes[guild.id],
          "chatchannel": chat_config.chat_channel_id if chat_config is not None else None,
          "lang": lang_code,
          "persona": chat_config.persona if chat_config is not None else None,
          "name": guild.name,
          "tier": 0,
          "icon": guild.icon.url if guild.icon is not None else None,
          "reddit_extract": reddit_config.enabled if reddit_config is not None else False,
          "channels": channels,
      }
      return web.json_response(response)

    @routes.get("/guilds/{gid}/moderation")
    async def get_moderation(request: web.Request) -> web.Response:
      gid = request.match_info["gid"]
      guild = bot.get_guild(int(gid, base=10))
      if guild is None:
        try:
          guild = await bot.fetch_guild(int(gid, base=10))
          if guild is None:
            return web.HTTPNotFound(reason="Guild not found")
        except Exception as e:
          return web.HTTPNotFound(reason=f"Guild not found: {e}")
      elif guild.unavailable:
        return web.HTTPBadGateway(reason="Guild is unavailable")

      if gid in self.bot.blacklist:
        return HTTPBlocked(reason="This server is blacklisted from the bot.")

      channels = [{
          "name": i.name,
          "id": str(i.id),
          "type": str(i.type),
          "position": i.position,
          "parent_id": i.category.id if i.category is not None else None,
      } for i in guild.channels if i.type in (discord.ChannelType.text, discord.ChannelType.category)]

      roles = [{
          "name": i.name,
          "id": str(i.id),
          "position": i.position,
          "color": i.color.value,
          "managed": i.managed
      } for i in guild.roles if not i.is_default() and not i.is_bot_managed() and not i.is_integration() and not i.is_premium_subscriber()]

      top_role = {"name": guild.me.top_role.name, "id": str(guild.me.top_role.id), "position": guild.me.top_role.position}

      automod_cog: Optional[AutoMod] = self.bot.get_cog("AutoMod")  # type: ignore
      automod_config: Optional[AutoModConfig] = automod_cog and await automod_cog.get_guild_config(int(gid, base=10))
      welcome_cog: Optional[Welcome] = self.bot.get_cog("Welcome")  # type: ignore
      welcome_config: Optional[WelcomeConfig] = welcome_cog and await welcome_cog.get_guild_config(int(gid, base=10))
      mod_logging_cog: Optional[ModLogging] = self.bot.get_cog("ModLogging")  # type: ignore
      mod_logging_config: Optional[LoggingConfig] = mod_logging_cog and await mod_logging_cog.get_guild_config(int(gid, base=10))

      response: GetModerationType = {
          "remove_invites": automod_config.remove_invites if automod_config is not None else None,
          "max_mentions": automod_config.max_mentions if automod_config is not None else None,
          "max_messages": automod_config.max_messages if automod_config is not None else None,
          "max_content": automod_config.max_content if automod_config is not None else None,
          "channels": channels,
          "top_role": top_role,
          "roles": roles,
          "tier": 0,
          "mute_role": str(automod_config.mute_role_id) if automod_config is not None else None,
          "whitelist": list(automod_config.automod_whitelist) if automod_config is not None else None,
          "mod_log_events": list(mod_logging_config.mod_log_events) if mod_logging_config is not None else None,
          "mod_log_channel_id": mod_logging_config.mod_log_channel_id if mod_logging_config is not None else None,
          "welcome": dict(
              channel_id=welcome_config.channel_id if welcome_config is not None and welcome_config.channel_id is not None else None,
              role_id=welcome_config.role_id if welcome_config is not None and welcome_config.role_id is not None else None,
              message=welcome_config.message if welcome_config is not None and welcome_config.message is not None else None,
          ),
          "blacklist": dict(
              words=automod_config.blacklisted_words if automod_config is not None else [],
              punishments=automod_config.blacklist_punishments if automod_config is not None else [],
          )
      }

      return web.json_response(response)

    @routes.get("/guilds/{gid}/music")
    async def get_music(request: web.Request) -> web.Response:
      gid = request.match_info["gid"]
      guild = bot.get_guild(int(gid, base=10))
      if guild is None:
        try:
          guild = await bot.fetch_guild(int(gid, base=10))
          if guild is None:
            return web.HTTPNotFound(reason="Guild not found")
        except Exception as e:
          return web.HTTPNotFound(reason=f"Guild not found: {e}")
      elif guild.unavailable:
        return web.HTTPBadGateway(reason="Guild is unavailable")

      if gid in self.bot.blacklist:
        return HTTPBlocked(reason="This server is blacklisted from the bot.")

      try:
        customsounds: list = await self.bot.pool.fetchval("SELECT customSounds FROM servers WHERE id=$1 LIMIT 1", str(guild.id))
      except Exception as e:
        return web.HTTPInternalServerError(reason=f"Failed to get custom sounds: {e}")

      response: GetMusicType = {
          "customsounds": customsounds,
          "tier": 0,
      }

      return web.json_response(response)

    @routes.get("/guilds/{gid}/commands")
    async def get_commands(request: web.Request) -> web.Response:
      gid = request.match_info["gid"]
      guild = bot.get_guild(int(gid, base=10))
      if guild is None:
        try:
          guild = await bot.fetch_guild(int(gid, base=10))
          if guild is None:
            return web.HTTPNotFound(reason="Guild not found")
        except Exception as e:
          return web.HTTPNotFound(reason=f"Guild not found: {e}")
      elif guild.unavailable:
        return web.HTTPBadGateway(reason="Guild is unavailable")

      if gid in self.bot.blacklist:
        return HTTPBlocked(reason="This server is blacklisted from the bot.")

      log_cog: Log = self.bot.get_cog("Log")  # type: ignore
      log_config: LogConfig = await log_cog.get_guild_config(int(gid, base=10))

      channels = [{
          "name": i.name,
          "id": str(i.id),
          "type": str(i.type),
          "position": i.position,
          "parent_id": i.category.id if i.category is not None else None,
      } for i in guild.channels if i.type in (discord.ChannelType.text, discord.ChannelType.category)]

      cogs = [
          {
              "name": cog.qualified_name,
              "description": cog.description,
              "commands": {
                  com.qualified_name: {
                      "name": com.qualified_name,
                      "description": com.help,
                      "enabled": bool(com.qualified_name not in log_config.disabled_commands),
                      "restricted": bool(com.qualified_name in log_config.restricted_commands),
                      "checks": False,
                      "subcommands": {
                          sub.qualified_name: {
                              "name": sub.qualified_name,
                              "description": sub.help,
                              "enabled": bool(sub.qualified_name not in log_config.disabled_commands),
                              "restricted": bool(sub.qualified_name in log_config.restricted_commands),
                              "checks": False,
                          } for sub in com.commands  # type: ignore
                      } if hasattr(com, "commands") else {}
                  } for com in cog.get_commands()}
          } for cog in self.bot.cogs.values() if len(cog.get_commands()) > 0 and cog.qualified_name not in ("Dev", "Config") and not cog.__cog_settings__.get("hidden", False)
      ]

      response: GetCommandsType = {
          "channels": channels,
          "cogs": cogs,
          "config": {
              "bot_channel": log_config.bot_channel if log_config is not None else None,
          }
      }

      return web.json_response(response)

    @routes.post("/guilds/{gid}/invalidate")
    async def guild_invalidate(request: web.Request) -> web.Response:
      gid = request.match_info["gid"]
      guild = bot.get_guild(int(gid, base=10))
      if guild is None:
        try:
          guild = await bot.fetch_guild(int(gid, base=10))
          if guild is None:
            return web.HTTPNotFound(reason="Guild not found")
        except Exception as e:
          return web.HTTPNotFound(reason=f"Guild not found: {e}")
      elif guild.unavailable:
        return web.HTTPBadGateway(reason="Guild is unavailable")

      if gid in self.bot.blacklist:
        return HTTPBlocked(reason="This server is blacklisted from the bot.")

      passes = 0
      cogs: List[Optional[CogConfig]] = [
          self.bot.get_cog("Moderation"),
          self.bot.get_cog("AutoMod"),
          self.bot.get_cog("Welcome"),
          self.bot.get_cog("Chat"),
          self.bot.get_cog("redditlink")  # type: ignore
      ]
      for cog in cogs:
        if cog is not None:
          cog.get_guild_config.invalidate(cog, int(gid, base=10))
          passes += 1

      self.bot.prefixes[int(gid, base=10)] = await self.bot.pool.fetchval("SELECT prefix FROM servers WHERE id=$1 LIMIT 1", str(gid))

      return web.json_response({"success": True, "passes": f"{passes}/{len(cogs)}"})

    # @routes.post("/patreon/activate/{uid}/{gid}")
    # async def patreon_activate(request: web.Request) -> web.Response:
    #   uid = request.match_info["uid"]
    #   gid = request.match_info["gid"]
    #   guild = bot.get_guild(int(gid, base=10))
    #   if guild is None:
    #     try:
    #       guild = await bot.fetch_guild(int(gid, base=10))
    #       if guild is None:
    #         return web.HTTPNotFound(reason="Guild not found")
    #     except Exception as e:
    #       return web.HTTPNotFound(reason=f"Guild not found: {e}")
    #   elif guild.unavailable:
    #     return web.HTTPBadGateway(reason="Guild is unavailable")

    #   if gid in self.bot.blacklist:
    #     return HTTPBlocked(reason="This server is blacklisted from the bot.")

    #   pat_cog: Optional[Patreons] = self.bot.get_cog("Patreons")  # type: ignore
    #   if pat_cog is None:
    #     return web.HTTPInternalServerError()

    #   patron_configs = await pat_cog.get_patrons()
    #   discord_ids = [i.id for i in patron_configs]
    #   if uid not in discord_ids:
    #     return web.HTTPForbidden(reason="User is not a patron")

    #   query = f"INSERT INTO patrons (user_id,tier,guild_ids) VALUES ($1,{config.PremiumTiersNew.tier_1.value},array[$2]::text[]) ON CONFLICT (user_id) DO UPDATE SET guild_ids=array_append(patrons.guild_ids,$2) WHERE NOT ($2=any(patrons.guild_ids));"
    #   await self.bot.pool.execute(query, str(uid), str(gid))

    #   return web.HTTPOk()

    # @routes.post("/patreon/deactivate/{uid}/{gid}")
    # async def patreon_deactivate(request: web.Request) -> web.Response:
    #   uid = request.match_info["uid"]
    #   gid = request.match_info["gid"]
    #   guild = bot.get_guild(int(gid, base=10))
    #   if guild is None:
    #     try:
    #       guild = await bot.fetch_guild(int(gid, base=10))
    #       if guild is None:
    #         return web.HTTPNotFound(reason="Guild not found")
    #     except Exception as e:
    #       return web.HTTPNotFound(reason=f"Guild not found: {e}")
    #   elif guild.unavailable:
    #     return web.HTTPBadGateway(reason="Guild is unavailable")

    #   if gid in self.bot.blacklist:
    #     return HTTPBlocked(reason="This server is blacklisted from the bot.")

    #   pat_cog: Optional[Patreons] = self.bot.get_cog("Patreons")  # type: ignore
    #   if pat_cog is None:
    #     return web.HTTPInternalServerError()

    #   patron_configs = await pat_cog.get_patrons()
    #   discord_ids = [i.id for i in patron_configs]
    #   if uid not in discord_ids:
    #     return web.HTTPForbidden(reason="User is not a patron")

    #   query = "UPDATE patrons SET guild_ids=array_remove(patrons.guild_ids,$1) WHERE user_id=$2 AND ($1=ANY(patrons.guild_ids));"
    #   await self.bot.pool.execute(query, str(gid), str(uid))

    #   return web.HTTPOk()

    # @routes.post("/patreon")
    # async def patron(secret: str, request: web.Request):
    #   assert request.content_length and request.content_length < 1000000, "Request content too fat"  # 1M
    #   digest, signature = request.headers['X-HUB-SIGNATURE'].split("=", 1)
    #   assert digest == "sha1", "Digest must be sha1"  # use a whitelist
    #   body = await request.content.read()
    #   h = hmac.HMAC(bytes(secret, "UTF8"), msg=body, digestmod=digest)
    #   assert h.hexdigest() == signature, "Bad signature"
    #   return json.loads(body.decode('UTF8'))

    try:
      ssl_ctx = None
      if self.bot.prod or self.bot.canary:
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(os.environ.get("SSLCERT", None), os.environ.get("SSLKEY", None))  # type: ignore

      app.add_routes(routes)
      for route in list(app.router.routes()):
        cors.add(route)

      self.runner = web.AppRunner(app)
      await self.runner.setup()
      self.site = web.TCPSite(self.runner, "0.0.0.0", self.port, ssl_context=ssl_ctx)
      await self.site.start()
    except Exception as e:
      log.exception(f"Failed to start aiohttp.web: {e}")
    else:
      log.info(f"aiohttp.web started on port {self.port}")


async def setup(bot):
  await bot.add_cog(API(bot))
