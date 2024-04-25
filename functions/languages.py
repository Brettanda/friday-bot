from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from typing import TYPE_CHECKING
from zipfile import ZipFile

import aiofiles
import asyncio
import aiofiles.os
from i18n import I18n

if TYPE_CHECKING:
  from index import Friday

log = logging.getLogger(__name__)


def extract_zip(path, zdir):
  with ZipFile(path, 'r') as zipf:
    zipf.extractall(zdir)


extract_zip = aiofiles.os.wrap(extract_zip)  # type: ignore
rmtree = aiofiles.os.wrap(shutil.rmtree)  # type: ignore
unlink = aiofiles.os.wrap(os.unlink)  # type: ignore


async def pull_languages(build_id: int, *, bot: Friday, lang_dir: str, base_url: str, key: str) -> None:
  locales_path = os.path.join(lang_dir, "locales")
  zip_path = os.path.join(lang_dir, "i18n_translations.zip")
  async with bot.session.get(f"{base_url}/translations/builds/{build_id}/download", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}) as resp:
    try:
      resp.raise_for_status()
    except Exception as e:
      log.error(e)
      raise e
    data = await resp.json()
    while data["data"].get("url", None) is None:
      await asyncio.sleep(1)
      async with bot.session.get(f"{base_url}/translations/builds/{build_id}/download", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}) as resp:
        try:
          resp.raise_for_status()
        except Exception as e:
          log.error(e)
          raise e
        data = await resp.json()

    url = data["data"]["url"]
  async with bot.session.get(url) as resp:
    async with aiofiles.open(zip_path, mode="wb+") as f:
      while True:
        try:
          chunk = await resp.content.read(1024)
          if not chunk:
            break
          await f.write(chunk)
        except Exception as e:
          log.error(e)
          raise e
    log.info("Downloaded zipfile of Crowdin translations")

  try:
    for fi in os.listdir(locales_path):
      fpath = os.path.join(locales_path, fi)
      try:
        if os.path.isfile(fpath):
          await unlink(fpath)
        elif os.path.isdir(fpath):
          await rmtree(fpath)
      except Exception:
        log.exception("Failed to remove %s", fi)
  except FileNotFoundError:
    pass
  log.info("Cleaned up i18n/locales")

  await extract_zip(zip_path, lang_dir)  # type: ignore
  log.info("Extracted zipfile of Crowdin translations")

  await unlink(zip_path)


async def load_languages(bot: Friday) -> None:
  bot.language_files = {}
  base_url = "https://api.crowdin.com/api/v2/projects/484775"
  key = os.environ["CROWDIN_KEY"]
  lang_dir = os.path.join(os.getcwd(), "i18n")
  log.debug(f"path {lang_dir!r}")

  if bot.cluster_idx == 0:
    async with bot.session.post(f"{base_url}/translations/builds", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}) as resp:
      try:
        resp.raise_for_status()
      except Exception as e:
        log.error(e)
        raise e
      data = await resp.json()
      build_id = data["data"]["id"]
      log.info("Built Crowdin translations")

      await pull_languages(
          build_id,
          bot=bot,
          lang_dir=lang_dir,
          base_url=base_url,
          key=key,
      )

  async with aiofiles.open(os.path.join(lang_dir, "en", "commands.json"), mode="r", encoding="utf8") as f:
    content = json.loads(await f.read())

    bot.language_files["en"] = I18n.from_dict(content)
    log.debug("Loaded Language 'en'")

  locales_path = os.path.join(lang_dir, "locales")
  for fi in os.listdir(locales_path):
    fpath = os.path.join(locales_path, fi)
    if os.path.isdir(fpath):
      json_fpath = os.path.join(fpath, "commands.json")
      async with aiofiles.open(json_fpath, "r", encoding="utf8") as f:
        content = json.loads(await f.read())

        bot.language_files[fi] = I18n.from_dict(content)
        log.debug(f"Loaded Language {fi!r}")

  log.info('Loaded %i languages (%s bytes)', len(bot.language_files), sys.getsizeof(bot.language_files))
