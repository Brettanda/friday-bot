import os
import ssl
from typing import TYPE_CHECKING

# import aiohttp_cors
from aiohttp import web
from nextcord.ext import commands

if TYPE_CHECKING:
  from index import Friday as Bot


class HTTPImATeaPot(web.HTTPClientError):
  "This is by far the best error code"
  status_code = 418

  @property
  def reason(self) -> str:
    return "I'm a teapot"


class API(commands.Cog):
  def __init__(self, bot: "Bot"):
    self.app = web.Application(logger=bot.logger, debug=not bot.prod and not bot.canary)
    self.runner = None
    self.site = None
    self.bot = bot
    self.log = bot.logger

    # TODO: Not sure how to choose which cluster to ping from API
    # Use something like port 4001 when clusters
    # But now there is ssl so idk what i will do when clusters lmao
    if self.bot.canary or self.bot.prod:
      self.port = 443  # + bot.cluster_idx
    else:
      self.port = 4001

    self.bot.loop.create_task(self.run(), name="Web")

  def cog_unload(self):
    self.bot.loop.create_task(self.runner.cleanup())

  async def get_guild_config(self, cog: str, guild_id: int):
    cog = self.bot.get_cog(cog)
    if cog is None:
      return None
    return await cog.get_guild_config(guild_id)

  async def run(self):  # noqa: C901
    app = self.app
    bot = self.bot
    # TODO: Add CORS support https://github.com/aio-libs/aiohttp-cors  allow_origin=["https://friday-bot.com"], allow_methods=["GET"]
    # cors = aiohttp_cors.setup(app)
    routes = web.RouteTableDef()

    # Adds too much complexity to the API
    # also don't think this needs to be private
    # @app.before_request
    # def before_request():
    #   if request.headers.get("Authorization") != os.environ.get("APIREQUESTS"):
    #     return abort(401)

    @routes.get("/")
    async def index(request: web.Request):
      response = web.HTTPSeeOther("https://youtu.be/dQw4w9WgXcQ")
      response.headers["Cache-Control"] = "no-cache, no-store, max-age=0, must-revalidate"
      response.headers["Pragma"] = "no-cache"
      response.headers["Expires"] = "Mon, 01 Jan 1990 00:00:00 GMT"
      return response

    @routes.get("/stats")
    async def stats(request: web.Request):
      return web.json_response({
          "guilds": len(bot.guilds),
          "members": sum(len(g.humans) for g in bot.guilds),
          "bot": {
              "is_ready": bot.is_ready(),
              "is_closed": bot.is_closed(),
              "ratelimited": bot.is_ws_ratelimited()
          },
          "shards": [
              {
                  "id": i.id,
                  "latency": i.latency,
                  "is_closed": i.is_closed(),
                  "ratelimited": i.is_ws_ratelimited(),
              } for i in bot.shards.values()
          ]
      })

    @routes.get("/invite")
    async def get_invite(request: web.Request):
      invite = bot.get_cog("Invite")
      if invite is None:
        return web.HTTPInternalServerError()

      response = web.HTTPMovedPermanently(invite.link)
      response.headers["Cache-Control"] = "no-cache, no-store, max-age=0, must-revalidate"
      response.headers["Pragma"] = "no-cache"
      response.headers["Expires"] = "Mon, 01 Jan 1990 00:00:00 GMT"
      return response

    @routes.get("/guilds")
    async def get_guilds(request: web.Request):
      if not hasattr(request.headers, "guilds"):
        return HTTPImATeaPot()
      if len(request.headers.guilds) == 0:
        return HTTPImATeaPot()

      guild_ids = [int(i, base=10) for i in request.headers.guilds.split(",")]
      guilds = []
      for guild_id in guild_ids:
        guild = bot.get_guild(guild_id)
        if guild is None:
          await bot.fetch_guild(guild_id)
        if guild is not None:
          guilds.append(guild)
      if len(guilds) == 0:
        return web.HTTPNotFound()

    @routes.get("/guilds/{gid}")
    async def get_guild(request: web.Request):
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

      text_channels = [{
          "name": i.name,
          "id": str(i.id),
          "type": str(i.type),
          "position": i.position
      } for i in guild.text_channels]

      chat_config = await self.get_guild_config("Chat", int(gid, base=10))

      return web.json_response({
          "prefix": bot.prefixes[guild.id],
          "chatchannel": chat_config.chat_channel_id if chat_config is not None else None,
          "lang": chat_config.lang if chat_config is not None else None,
          "persona": chat_config.persona if chat_config is not None else None,
          "name": guild.name,
          "icon": guild.icon.url,
          "text_channels": text_channels,
      })

    @routes.get("/guilds/{gid}/moderation")
    async def get_moderation(request: web.Request):
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

      text_channels = [{
          "name": i.name,
          "id": str(i.id),
          "type": str(i.type),
          "position": i.position
      } for i in guild.text_channels]

      roles = [{
          "name": i.name,
          "id": str(i.id),
          "position": i.position,
          "managed": i.managed
      } for i in guild.roles if not i.is_default() and not i.is_bot_managed() and not i.is_integration() and not i.is_premium_subscriber()]

      top_role = {"name": guild.me.top_role.name, "id": str(guild.me.top_role.id), "position": guild.me.top_role.position}

      automod_config = await self.get_guild_config("AutoMod", int(gid, base=10))
      welcome_config = await self.get_guild_config("Welcome", int(gid, base=10))

      return web.json_response({
          "guild": dict(
              remove_invites=automod_config.remove_invites if automod_config is not None else None,
              max_mentions=automod_config.max_mentions if automod_config is not None else None,
              max_messages=automod_config.max_messages if automod_config is not None else None,
              max_content=automod_config.max_content if automod_config is not None else None,
              text_channels=text_channels,
              top_role=top_role,
              roles=roles
          ),
          "welcome": dict(
              channel_id=welcome_config.channel_id if welcome_config is not None else None,
              role_id=welcome_config.role_id if welcome_config is not None else None,
              message=welcome_config.message if welcome_config is not None else None,
          ),
          "blacklist": dict(
              words=automod_config.blacklisted_words if automod_config is not None else [],
              punishments=automod_config.blacklist_punishments if automod_config is not None else [],
          )
      })

    @routes.get("/guilds/{gid}/music")
    async def get_music(request: web.Request):
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

      try:
        customsounds = await self.bot.db.query("SELECT customSounds FROM servers WHERE id=$1 LIMIT 1", str(guild.id))
      except Exception as e:
        return web.HTTPInternalServerError(reason=f"Failed to get custom sounds: {e}")

      return web.json_response({
          "guild": dict(
              customsounds=customsounds
          )
      })

    self.log.info(f"Starting aiohttp.web on port {self.port}")
    try:
      ssl_ctx = None
      if self.bot.prod or self.bot.canary:
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(os.environ.get("SSLCERT", None), os.environ.get("SSLKEY", None))

      app.add_routes(routes)
      self.runner = web.AppRunner(app)
      await self.runner.setup()
      self.site = web.TCPSite(self.runner, "0.0.0.0", self.port, ssl_context=ssl_ctx)
      await self.site.start()
    except Exception as e:
      self.log.exception(f"Failed to start aiohttp.web: {e}")
    else:
      self.log.info(f"aiohttp.web started on port {self.port}")


def setup(bot):
  bot.add_cog(API(bot))
