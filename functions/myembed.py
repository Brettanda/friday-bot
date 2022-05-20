from __future__ import annotations

from typing import Collection, Optional, Union, Any

import discord

from functions.messagecolors import MessageColors


MISSING = discord.utils.MISSING


class embed(discord.Embed):
  def __init__(self,
               *,
               author_name: Optional[str] = None,
               author_url: Optional[str] = None,
               author_icon: Optional[str] = None,
               image: Optional[str] = None,
               thumbnail: Optional[str] = None,
               footer: Optional[str] = None,
               footer_icon: Optional[str] = None,
               fieldstitle: Optional[Union[Any, Collection[Any]]] = None,
               fieldsval: Optional[Union[Any, Collection[Any]]] = None,
               fieldsin: Optional[Union[bool, Collection[bool]]] = None,
               **kwargs) -> None:
    super().__init__(**kwargs)
    if self.color is MISSING or self.color is None:
      self.color = MessageColors.default()

    if author_name:
      self.set_author(name=author_name, url=author_url, icon_url=author_icon)

    self.set_image(url=image)
    self.set_thumbnail(url=thumbnail)
    self.set_footer(text=footer, icon_url=footer_icon)

    if fieldstitle and fieldsin is None:
      fieldsin = [True] * len(fieldstitle)

    if fieldstitle and fieldsval and fieldsin is not None:
      if isinstance(fieldstitle, str) and isinstance(fieldsval, str) and isinstance(fieldsin, bool):
        self.add_field(name=fieldstitle, value=fieldsval, inline=fieldsin)
      else:
        for t, v, i in zip(fieldstitle, fieldsval, fieldsin):  # type: ignore
          self.add_field(name=t, value=v, inline=i)
