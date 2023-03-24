import asyncio
import contextlib
import logging
import multiprocessing
import os
import signal
import sys
import time
from logging.handlers import RotatingFileHandler
from typing import List, Optional

import discord
import requests
from discord.utils import _ColourFormatter

from index import Friday

try:
  import uvloop  # type: ignore
except ImportError:
  pass
else:
  asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

PROD = len(sys.argv) > 1 and (sys.argv[1] == "--prod" or sys.argv[1] == "--production")
CANARY = len(sys.argv) > 1 and (sys.argv[1] == "--canary")


LEVEL_COLOURS = _ColourFormatter.LEVEL_COLOURS

FORMATS = {
        level: logging.Formatter(
            '\x1b[30;1m{asctime}\x1b[0m ' + colour + '{levelname:<8}\x1b[0m \x1b[34m{name:<16}\x1b[0m {message}',
            '%H:%M:%S',
            style="{"
        )
        for level, colour in LEVEL_COLOURS
}

_ColourFormatter.FORMATS = FORMATS


class _ColourFormatterFile(_ColourFormatter):
  @property
  def FORMATS(self):
    return {
        level: logging.Formatter(
            '{asctime} {levelname:<8} {name:<16} {message}',
            '%Y-%m-%d %H:%M:%S',
            style="{"
        )
        for level, colour in self.LEVEL_COLOURS
    }


class _ColourFormatterShort(_ColourFormatter):
  @property
  def FORMATS(self):
    return {
        level: logging.Formatter(
            '\x1b[30;1m{asctime}\x1b[0m ' + colour + '{levelname:<8}\x1b[0m \x1b[34m{name:<16}\x1b[0m {message}',
            '%H:%M:%S',
            style="{"
        )
        for level, colour in self.LEVEL_COLOURS
    }


class RemoveDuplicate(logging.Filter):
  def __init__(self):
    super().__init__(name='discord')

  def filter(self, record):
    if "discord" in record.name:
      return False
    return True


class RemoveNoise(logging.Filter):
  def __init__(self):
    super().__init__(name='discord.state')

  def filter(self, record):
    if record.levelname == 'WARNING' and 'referencing an unknown' in record.msg:
      return False
    return True


@contextlib.contextmanager
def setup_logging(name: Optional[str] = ...):
  """The default logger for the bot."""
  log = logging.getLogger()

  try:
    # __enter__
    max_bytes = 8 * 1024 * 1024  # 8 MiB
    logging.getLogger("discord").setLevel(logging.INFO)
    logging.getLogger("discord").setLevel(logging.INFO)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger('discord.state').addFilter(RemoveNoise())
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    log.setLevel(logging.INFO)

    filehandler = RotatingFileHandler(filename="logging.log", encoding="utf-8", mode="w", maxBytes=max_bytes, backupCount=5)
    filehandler.setFormatter(_ColourFormatterFile())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_ColourFormatterShort())
    handler.addFilter(RemoveDuplicate())

    log.addHandler(filehandler)
    log.addHandler(handler)

    yield
  finally:
    # __exit__
    handlers = log.handlers[:]
    for hdlr in handlers:
      hdlr.close()
      log.removeHandler(hdlr)


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


TOKEN = os.environ.get('TOKENTEST')
if len(sys.argv) > 1:
  if PROD:
    TOKEN = os.environ.get("TOKEN")
  elif CANARY:
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

    self.prod = PROD
    self.canary = CANARY

    self.log = logging.getLogger("Launcher")

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
    self.log.info(f"Successfully got shard count of {content['shards']} ({data.status_code}, {data.reason})")
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
    self.log.info(f"Preparing {len(size)} clusters")
    for shard_ids in size:
      self.cluster_queue.append(Cluster(self, next(NAMES), shard_ids, len(shards)))

    await self.start_cluster()
    self.keep_alive = self.loop.create_task(self.rebooter())
    self.keep_alive.add_done_callback(self.task_complete)
    self.log.info(f"Startup completed in {time.perf_counter()-self.init}s")

  async def shutdown(self):
    self.log.info("Shutting down clusters")
    self.alive = False
    if self.keep_alive:
      self.keep_alive.cancel()
    for cluster in self.clusters:
      cluster.stop()
    self.cleanup()

  async def rebooter(self):
    while self.alive:
      if not self.clusters:
        self.log.warning("All clusters appear to be dead")
        asyncio.ensure_future(self.shutdown())
      to_remove = []
      for cluster in self.clusters:
        if cluster.process and not cluster.process.is_alive():
          if cluster.process.exitcode != 0:
            self.log.info(f"CLUSTER #{cluster.name} exited with code {cluster.process.exitcode}")
            self.log.info(f"Restarting cluster #{cluster.name}")
            await cluster.start()
          else:
            self.log.info(f"CLUSTER #{cluster.name} is dead")
            to_remove.append(cluster)
            cluster.stop()
      for rem in to_remove:
        self.clusters.remove(rem)
      await asyncio.sleep(5)

  async def start_cluster(self):
    for cluster in self.cluster_queue:
      self.clusters.append(cluster)
      self.log.info(f"Starting Cluster #{cluster.name}")
      self.loop.create_task(cluster.start())
      await asyncio.sleep(0.5)


class Cluster:
  def __init__(self, launcher: Launcher, name: str, shard_ids: list, max_shards: int):
    self.launcher: Launcher = launcher
    self.process: Optional[multiprocessing.Process] = None
    self.name: str = name

    self.log = log = logging.getLogger(f"Cluster#{name}")
    log.info(f"Initialized with shard ids {shard_ids}, total shards {max_shards}")

    self.kwargs = dict(
        token=TOKEN,
        shard_ids=shard_ids,
        shard_count=max_shards,
        cluster=self,  # type: ignore
        cluster_name=name,
        cluster_idx=CLUSER_NAMES.index(name),
        start=True
    )

  # def wait_close(self):
  #   return self.process.join()

  async def start(self, *, force: bool = False) -> bool:
    if self.process and self.process.is_alive():
      if not force:
        self.log.warning("Start called with already running cluster, pass `force=True` to override")
        return False
      self.log.info("Terminating existing process")
      self.process.terminate()
      self.process.close()

    self.process = multiprocessing.Process(target=Friday, kwargs=self.kwargs, daemon=True)
    self.process.start()
    self.log.info(f"Process started with PID {self.process.pid}")

    return True

  def stop(self, sign=signal.SIGINT) -> None:
    self.log.info(f"Shutting down with signal {sign!r}")
    if self.process and self.process.pid:
      try:
        os.kill(self.process.pid, sign)
      except ProcessLookupError:
        pass


if __name__ == "__main__":
  loop = asyncio.get_event_loop()
  with setup_logging("Cluster#Launcher"):
    laun = Launcher(loop)
    laun.start()
