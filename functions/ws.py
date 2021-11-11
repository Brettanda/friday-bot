from datetime import timedelta
# import os
from threading import Thread
from typing import TYPE_CHECKING

from quart import Quart, abort, jsonify, redirect, request
from quart_cors import cors
from quart_rate_limiter import RateLimiter, rate_limit

if TYPE_CHECKING:
  from index import Friday as Bot


class WebServer:
  def __init__(self, bot: "Bot"):
    self.app = Quart(__name__)
    self.rate_limiter = RateLimiter(self.app)
    self.app = cors(self.app, allow_origin=["https://friday-bot.com"], allow_methods=["GET"])
    self.bot = bot
    self.log = bot.logger
    self.thread = None

    # TODO: Not sure how to choose which cluster to ping from API
    # Use something like port 4001 when clusters
    if self.bot.canary or self.bot.prod:
      self.port = 80  # + bot.cluster_idx
    else:
      self.port = 4001

  def start(self):
    self.bot.loop.create_task(self.run())

  async def get_guild_config(self, cog: str, guild_id: int):
    cog = self.bot.get_cog(cog)
    if cog is None:
      return None
    return await cog.get_guild_config(guild_id)

  async def run(self):
    app = self.app
    bot = self.bot

    # Adds too much complexity to the API
    # also don't think this needs to be private
    # @app.before_request
    # def before_request():
    #   if request.headers.get("Authorization") != os.environ.get("APIREQUESTS"):
    #     return abort(401)

    @app.route("/")
    async def index():
      response = redirect("https://youtu.be/dQw4w9WgXcQ", code=303)
      response.headers["Cache-Control"] = "no-cache, no-store, max-age=0, must-revalidate"
      response.headers["Pragma"] = "no-cache"
      response.headers["Expires"] = "Mon, 01 Jan 1990 00:00:00 GMT"
      return response

    @app.route("/stats")
    async def stats():
      return jsonify(
          guilds=len(bot.guilds),
          members=sum(len(g.humans) for g in bot.guilds),
          bot={
              "is_ready": bot.is_ready(),
              "is_closed": bot.is_closed(),
              "ratelimited": bot.is_ws_ratelimited()
          },
          shards=[
              {
                  "id": i.id,
                  "latency": i.latency,
                  "is_closed": i.is_closed(),
                  "ratelimited": i.is_ws_ratelimited(),
              } for i in bot.shards.values()
          ]
      )

    @app.route("/invite")
    async def get_invite():
      invite = bot.get_cog("Invite")
      if invite is None:
        return abort(500)

      response = redirect(invite.link, code=301)
      response.headers["Cache-Control"] = "no-cache, no-store, max-age=0, must-revalidate"
      response.headers["Pragma"] = "no-cache"
      response.headers["Expires"] = "Mon, 01 Jan 1990 00:00:00 GMT"
      return response

    @app.route("/guilds")
    @rate_limit(5, timedelta(seconds=10))
    async def get_guilds():
      if not hasattr(request.headers, "guilds"):
        return abort(418)
      if len(request.headers.guilds) == 0:
        return abort(418)

      guild_ids = [int(i, base=10) for i in request.headers.guilds.split(",")]
      guilds = []
      for guild_id in guild_ids:
        guild = bot.get_guild(guild_id)
        if guild is None:
          await bot.fetch_guild(guild_id)
        if guild is not None:
          guilds.append(guild)
      if len(guilds) == 0:
        return abort(404)

    @app.route("/guilds/<gid>")
    @rate_limit(5, timedelta(seconds=10))
    async def get_guild(gid):
      guild = bot.get_guild(int(gid, base=10))
      if guild is None:
        try:
          guild = await bot.fetch_guild(int(gid, base=10))
          if guild is None:
            return jsonify(error="Guild not found"), 404

        except Exception as e:
          return jsonify(error=f"Guild not found: {e}"), 404
      elif guild.unavailable:
        return jsonify(unavailable=False), 502

      text_channels = [{
          "name": i.name,
          "id": str(i.id),
          "type": str(i.type),
          "position": i.position
      } for i in guild.text_channels]

      chat_config = await self.get_guild_config("Chat", int(gid, base=10))

      return jsonify(
          prefix=bot.prefixes[guild.id],
          chatchannel=chat_config.chat_channel_id if chat_config is not None else None,
          lang=chat_config.lang if chat_config is not None else None,
          persona=chat_config.persona if chat_config is not None else None,
          name=guild.name,
          icon=guild.icon.url,
          text_channels=text_channels,
      )

    @app.route("/guilds/<gid>/moderation")
    @rate_limit(5, timedelta(seconds=10))
    async def get_moderation(gid):
      guild = bot.get_guild(int(gid, base=10))
      if guild is None:
        try:
          guild = await bot.fetch_guild(int(gid, base=10))
          if guild is None:
            return jsonify(error="Guild not found"), 404
        except Exception as e:
          return jsonify(error=f"Guild not found: {e}"), 404
      elif guild.unavailable:
        return jsonify(unavailable=False), 502

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

      automod_config = await self.get_guild_config("Automod", int(gid, base=10))
      welcome_config = await self.get_guild_config("Welcome", int(gid, base=10))

      return jsonify(
          guild=dict(
              remove_invites=automod_config.remove_invites if automod_config is not None else None,
              max_mentions=automod_config.max_mentions if automod_config is not None else None,
              max_messages=automod_config.max_messages if automod_config is not None else None,
              max_content=automod_config.max_content if automod_config is not None else None,
              text_channels=text_channels,
              top_role=top_role,
              roles=roles
          ), welcome=dict(
              channel_id=welcome_config.channel_id if welcome_config is not None else None,
              role_id=welcome_config.role_id if welcome_config is not None else None,
              message=welcome_config.message if welcome_config is not None else None,
          ), blacklist=dict(
              words=automod_config.blacklist if automod_config is not None else None,
          )
      )

    @app.route("/guilds/<gid>/music")
    @rate_limit(5, timedelta(seconds=10))
    async def get_music(gid):
      guild = bot.get_guild(int(gid, base=10))
      if guild is None:
        try:
          guild = await bot.fetch_guild(int(gid, base=10))
          if guild is None:
            return jsonify(error="Guild not found"), 404
        except Exception as e:
          return jsonify(error=f"Guild not found: {e}"), 404
      elif guild.unavailable:
        return jsonify(unavailable=False), 502

      customsounds = await self.bot.db.query("SELECT customSounds FROM servers WHERE id=$1 LIMIT 1", str(guild.id))

      return jsonify(
          guild=dict(
              customsounds=customsounds
          )
      )

    self.log.info(f"Starting Quart on port {self.port}")
    try:
      await app.run_task(debug=True, host="0.0.0.0", port=self.port, use_reloader=False)
    except Exception as e:
      self.log.exception(f"Failed to start Quart: {e}")

  def keep_alive(self):
    t = Thread(target=self.start, daemon=True)
    t.name = "Web"
    t.start()
    self.thread = t
    return t
