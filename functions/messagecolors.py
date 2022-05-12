from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Colour

if TYPE_CHECKING:
  from typing_extensions import Self


class MessageColors(Colour):
  MUSIC = 0x7BDCFC
  SOUPTIME = 0xFFD700
  NOU = 0xFFD700
  MEME = 0x00A2E8
  RPS = 0xBAFAE5
  LOGGING = 0xFFD700
  ERROR = 0xD40000
  DEFAULT = 0xFDFDFD

  @classmethod
  def music(cls) -> Self:
    return cls(0x7BDCFC)

  @classmethod
  def souptime(cls) -> Self:
    return cls(0xFFD700)

  @classmethod
  def nou(cls) -> Self:
    return cls(0xFFD700)

  @classmethod
  def meme(cls) -> Self:
    return cls(0x00A2E8)

  @classmethod
  def rps(cls) -> Self:
    return cls(0xBAFAE5)

  @classmethod
  def logging(cls) -> Self:
    return cls(0xFFD700)

  @classmethod
  def error(cls) -> Self:
    return cls(0xD40000)

  @classmethod
  def default(cls) -> Self:
    return cls(0xFDFDFD)
