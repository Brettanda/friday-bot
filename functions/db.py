from __future__ import annotations

import datetime
import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import TypedDict

import asyncpg
import click

log = logging.getLogger(__name__)


class Revisions(TypedDict):
  # The version key represents the current activated version
  # So v1 means v1 is active and the next revision should be v2
  # In order for this to work the number has to be monotonically increasing
  # and have no gaps
  version: int
  database_uri: str


REVISION_FILE = re.compile(r'(?P<kind>V|U)(?P<version>[0-9]+)__(?P<description>.+).sql')


class Revision:
  __slots__ = ('kind', 'version', 'description', 'file')

  def __init__(self, *, kind: str, version: int, description: str, file: Path) -> None:
    self.kind: str = kind
    self.version: int = version
    self.description: str = description
    self.file: Path = file

  @classmethod
  def from_match(cls, match: re.Match[str], file: Path):
    return cls(
        kind=match.group('kind'), version=int(match.group('version')), description=match.group('description'), file=file
    )


class Migrations:
  def __init__(self, *, filename: str = 'migrations/revisions.json'):
    self.filename: str = filename
    self.root: Path = Path(filename).parent
    self.revisions: dict[int, Revision] = self.get_revisions()
    self.load()

  def ensure_path(self) -> None:
    self.root.mkdir(exist_ok=True)

  def load_metadata(self) -> Revisions:
    try:
      with open(self.filename, 'r', encoding='utf-8') as fp:
        return json.load(fp)
    except FileNotFoundError:
      return {
          'version': 0,
          'database_uri': os.environ["DBURL"],
      }

  def get_revisions(self) -> dict[int, Revision]:
    result: dict[int, Revision] = {}
    for file in self.root.glob('*.sql'):
      match = REVISION_FILE.match(file.name)
      if match is not None:
        rev = Revision.from_match(match, file)
        result[rev.version] = rev

    return result

  def dump(self) -> Revisions:
    return {
        'version': self.version,
        'database_uri': self.database_uri,
    }

  def load(self) -> None:
    self.ensure_path()
    data = self.load_metadata()
    self.version: int = data['version']
    self.database_uri: str = data['database_uri']

  def save(self):
    temp = f'{self.filename}.{uuid.uuid4()}.tmp'
    with open(temp, 'w', encoding='utf-8') as tmp:
      json.dump(self.dump(), tmp)

    # atomically move the file
    os.replace(temp, self.filename)

  def is_next_revision_taken(self) -> bool:
    return self.version + 1 in self.revisions

  @property
  def ordered_revisions(self) -> list[Revision]:
    return sorted(self.revisions.values(), key=lambda r: r.version)

  def create_revision(self, reason: str, *, kind: str = 'V') -> Revision:
    cleaned = re.sub(r'\s', '_', reason)
    filename = f'{kind}{self.version + 1}__{cleaned}.sql'
    path = self.root / filename

    stub = (
        f'-- Revises: V{self.version}\n'
        f'-- Creation Date: {datetime.datetime.utcnow()} UTC\n'
        f'-- Reason: {reason}\n\n'
    )

    with open(path, 'w', encoding='utf-8', newline='\n') as fp:
      fp.write(stub)

    self.save()
    return Revision(kind=kind, description=reason, version=self.version + 1, file=path)

  async def upgrade(self, connection: asyncpg.Connection) -> int:
    ordered = self.ordered_revisions
    successes = 0
    async with connection.transaction():
      for revision in ordered:
        if revision.version > self.version:
          sql = revision.file.read_text('utf-8')
          await connection.execute(sql)
          successes += 1

    self.version += successes
    self.save()
    return successes

  def display(self) -> None:
    ordered = self.ordered_revisions
    for revision in ordered:
      if revision.version > self.version:
        sql = revision.file.read_text('utf-8')
        click.echo(sql)


async def create_pool() -> asyncpg.Pool:
  def _encode_jsonb(value):
    return json.dumps(value)

  def _decode_jsonb(value):
    return json.loads(value)

  async def init(con):
    await con.set_type_codec(
        'jsonb',
        schema='pg_catalog',
        encoder=_encode_jsonb,
        decoder=_decode_jsonb,
        format='text',
    )

  return await asyncpg.create_pool(
      os.environ["DBURL"],
      init=init,
      command_timeout=60,
      max_size=20,
      min_size=20,
  )
