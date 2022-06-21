import asyncio
import logging
import multiprocessing
import os
import signal
import sys
import time
from typing import Optional, List
from logging.handlers import RotatingFileHandler

import discord
import requests

from index import Friday


def get_logger(name: Optional[str] = ...) -> logging.Logger:
  """The default logger for the bot."""

  max_bytes = 8 * 1024 * 1024  # 8 MiB
  logging.getLogger("discord").setLevel(logging.INFO)
  logging.getLogger("discord.http").setLevel(logging.WARNING)

  log = logging.getLogger(name)
  log.setLevel(logging.INFO)

  filehandler = RotatingFileHandler(filename="logging.log", encoding="utf-8", mode="w", maxBytes=max_bytes, backupCount=5)
  filehandler.setFormatter(logging.Formatter("%(asctime)s:%(name)s:%(levelname)-8s%(message)s"))

  handler = logging.StreamHandler(sys.stdout)
  handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s: %(message)s"))

  log.handlers = [handler, filehandler]
  return log


logger = get_logger("Cluster#Launcher")


CLUSER_NAMES = (
    "Jarvis",
    "Karen",
    "Ultron",
    "Edith",
    "Virgil",
    "Plato",
    "Homer",
    "Jocasta",
)

NAMES = iter(CLUSER_NAMES)

prod = len(sys.argv) > 1 and (sys.argv[1] == "--prod" or sys.argv[1] == "--production")
canary = len(sys.argv) > 1 and (sys.argv[1] == "--canary")

TOKEN = os.environ.get('TOKENTEST')
if len(sys.argv) > 1:
  if prod:
    TOKEN = os.environ.get("TOKEN")
  elif canary:
    TOKEN = os.environ.get("TOKENCANARY")


class Launcher:
  def __init__(self, loop: asyncio.AbstractEventLoop):
    self.cluster_queue: List[Cluster] = []
    self.clusters: List[Cluster] = []

    self.fut = None
    self.loop = loop
    self.alive = True

    self.keep_alive = None
    self.init = time.perf_counter()

    self.prod = prod
    self.canary = canary

  def get_shard_count(self) -> int:
    data = requests.get(
        "https://discord.com/api/v10/gateway/bot",
        headers={
            "Authorization": f"Bot {TOKEN}",
            "User-Agent": f'DiscordBot ({discord.__author__} {discord.__version__}) Python/{sys.version_info.major}.{sys.version_info.minor}'
        }
    )
    data.raise_for_status()
    content = data.json()
    logger.info(f"Successfully got shard count of {content['shards']} ({data.status_code}, {data.reason})")
    return content["shards"]

  def start(self):
    self.fut = asyncio.ensure_future(self.startup(), loop=self.loop)

    try:
      self.loop.run_forever()
    except KeyboardInterrupt:
      self.loop.run_until_complete(self.shutdown())
    finally:
      self.cleanup()

  def cleanup(self):
    self.loop.stop()
    try:
      self.loop.close()
    except Exception:
      pass

  def task_complete(self, task):
    if task.exception():
      task.print_stack()
      self.keep_alive = self.loop.create_task(self.rebooter())
      self.keep_alive.add_done_callback(self.task_complete)

  async def startup(self):
    shards = list(range(self.get_shard_count()))
    max_shards = 5
    size = [shards[x:x + max_shards] for x in range(0, len(shards), max_shards)]
    logger.info(f"Preparing {len(size)} clusters")
    for shard_ids in size:
      self.cluster_queue.append(Cluster(self, next(NAMES), shard_ids, len(shards)))

    await self.start_cluster()
    self.keep_alive = self.loop.create_task(self.rebooter())
    self.keep_alive.add_done_callback(self.task_complete)
    logger.info(f"Startup completed in {time.perf_counter()-self.init}s")

  async def shutdown(self):
    logger.info("Shutting down clusters")
    self.alive = False
    if self.keep_alive:
      self.keep_alive.cancel()
    for cluster in self.clusters:
      cluster.stop()
    self.cleanup()

  async def rebooter(self):
    while self.alive:
      if not self.clusters:
        logger.warning("All clusters appear to be dead")
        asyncio.ensure_future(self.shutdown())
      to_remove = []
      for cluster in self.clusters:
        if cluster.process and not cluster.process.is_alive():
          if cluster.process.exitcode != 0:
            logger.info(f"CLUSTER #{cluster.name} exited with code {cluster.process.exitcode}")
            logger.info(f"Restarting cluster #{cluster.name}")
            await cluster.start()
          else:
            logger.info(f"CLUSTER #{cluster.name} is dead")
            to_remove.append(cluster)
            cluster.stop()
      for rem in to_remove:
        self.clusters.remove(rem)
      await asyncio.sleep(5)

  async def start_cluster(self):
    for cluster in self.cluster_queue:
      self.clusters.append(cluster)
      logger.info(f"Starting Cluster #{cluster.name}")
      self.loop.create_task(cluster.start())
      await asyncio.sleep(0.5)


class Cluster:
  def __init__(self, launcher: Launcher, name: str, shard_ids: list, max_shards: int):
    self.launcher: Launcher = launcher
    self.process: Optional[multiprocessing.Process] = None
    self.name: str = name

    self.logger = get_logger(f"Cluster#{name}")
    self.logger.info(f"Initialized with shard ids {shard_ids}, total shards {max_shards}")

    self.kwargs = dict(
        token=TOKEN,
        shard_ids=shard_ids,
        shard_count=max_shards,
        cluster=self,  # type: ignore
        cluster_name=name,
        cluster_idx=CLUSER_NAMES.index(name),
        logger=self.logger,
        start=True
    )

  # def wait_close(self):
  #   return self.process.join()

  async def start(self, *, force: bool = False) -> bool:
    if self.process and self.process.is_alive():
      if not force:
        self.logger.warning("Start called with already running cluster, pass `force=True` to override")
        return False
      self.logger.info("Terminating existing process")
      self.process.terminate()
      self.process.close()

    self.process = multiprocessing.Process(target=Friday, kwargs=self.kwargs, daemon=True)
    self.process.start()
    self.logger.info(f"Process started with PID {self.process.pid}")

    return True

  def stop(self, sign=signal.SIGINT) -> None:
    self.logger.info(f"Shutting down with signal {sign!r}")
    if self.process and self.process.pid:
      try:
        os.kill(self.process.pid, sign)
      except ProcessLookupError:
        pass


if __name__ == "__main__":
  loop = asyncio.get_event_loop()
  Launcher(loop).start()
