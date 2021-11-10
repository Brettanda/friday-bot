import asyncio
# import os
from threading import Thread
from typing import TYPE_CHECKING

from flask import Flask, jsonify  # , request  , abort

if TYPE_CHECKING:
  from index import Friday as Bot


class WebServer:
  def __init__(self, bot: "Bot"):
    self.app = Flask(__name__)
    self.bot = bot
    self.log = bot.logger
    self.thread = None

    # TODO: Not sure how to choose which cluster to ping from API
    self.flask_port = 4001 + bot.cluster_idx

  def run(self):
    app = self.app
    bot = self.bot

    # Adds too much complexity to the API
    # also don't think this needs to be private
    # @app.before_request
    # def before_request():
    #   if request.headers.get("Authorization") != os.environ.get("APIREQUESTS"):
    #     return abort(401)

    @app.errorhandler(401)
    def unauthorized(*args, **kwargs):
      return jsonify(code=401, message="Unauthorized"), 401

    @app.errorhandler(404)
    def not_found(*args, **kwargs):
      return jsonify(code=404, message="Not found"), 404

    @app.route("/guilds/<gid>")
    def get_guild(gid):
      guild = bot.get_guild(int(gid, base=10))
      if guild is None:
        try:
          guild = asyncio.get_event_loop() \
              .run_until_complete(bot.fetch_guild(int(gid, base=10)))
          if guild is None:
            return jsonify(error="Guild not found"), 404

        except Exception as e:
          return jsonify(error=f"Guild not found: {e}"), 404
      elif guild.unavailable:
        return jsonify(unavailable=False), 502

      text_channels = [{
          "name": i.name,
          "id": str(i.id),
          "type": type(i).__name__,
          "position": i.position
      } for i in guild.text_channels]

      roles = [{
          "name": i.name,
          "id": str(i.id),
          "position": i.position,
          "managed": i.managed
      } for i in guild.roles]

      top_role = {"name": guild.me.top_role.name, "id": str(guild.me.top_role.id), "position": guild.me.top_role.position}

      return jsonify(
          name=guild.name,
          icon=guild.icon.url,
          channels=text_channels,
          top_role=top_role,
          roles=roles)

    self.log.info(f"Starting Flask on port {self.flask_port}")
    try:
      app.run(host="0.0.0.0", port=self.flask_port)
    except Exception as e:
      self.log.error(f"Failed to start Flask: {e}")

  def keep_alive(self):
    t = Thread(target=self.run, daemon=True)
    t.start()
    self.thread = t
    return t
