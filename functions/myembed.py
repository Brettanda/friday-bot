from functions.messagecolors import MessageColors
import discord

from typing import Union
from typing_extensions import TYPE_CHECKING

MISSING = discord.utils.MISSING

if TYPE_CHECKING:
  from .custom_contexts import MyContext

# class Embed():
#   def __init__(self,MessageColors):
#     self.MessageColors = MessageColors


def embed(
        title: str = "Text",
        description: str = "",
        color: discord.Colour = MISSING,
        author_name: str = MISSING,
        author_url: str = MISSING,
        author_icon: str = MISSING,
        image: str = MISSING,
        thumbnail: str = MISSING,
        footer: str = MISSING,
        footer_icon: str = MISSING,
        ctx: "MyContext" = MISSING,
        fieldstitle: Union[str, list] = MISSING,
        fieldsval: Union[str, list] = MISSING,
        fieldsin: Union[bool, list] = MISSING,
        url: str = MISSING, **kwargs) -> discord.Embed:
  """My Custom embed function"""
  if color is MISSING or color is None:
    color = MessageColors.DEFAULT
  r = discord.Embed(title=title, description=description, color=color, **kwargs)

  if image is not MISSING and image is not None:
    r.set_image(url=image)

  if thumbnail is not MISSING and thumbnail is not None:
    r.set_thumbnail(url=thumbnail)

  # if len(fieldstitle) > 0 and len(fieldsval) > 0:
  if fieldstitle is not MISSING and fieldsval is not MISSING and isinstance(fieldstitle, list) and isinstance(fieldsval, list):
    if len(fieldstitle) > 0 and len(fieldsval) > 0:
      if len(fieldstitle) == len(fieldsval):
        x = 0
        for i in fieldstitle:
          r.add_field(name=i, value=fieldsval[x], inline=fieldsin[x] if isinstance(fieldsin, list) and fieldsin is not MISSING else True)
          x += 1
      else:
        raise TypeError("fieldstitle and fieldsval must have the same number of elements")
  elif isinstance(fieldstitle, str) and isinstance(fieldsval, str) and isinstance(fieldsin, bool):
    r.add_field(name=fieldstitle, value=fieldsval, inline=fieldsin if isinstance(fieldsin, bool) and fieldsin is not MISSING else True)

  if author_name is not MISSING and author_name is not None and author_url is not MISSING and author_url is not None and author_icon is not MISSING and author_icon is not None:
    r.set_author(name=author_name, url=author_url, icon_url=author_icon)
  elif author_name is not MISSING and author_name is not None and author_url is not MISSING and author_url is not None:
    r.set_author(name=author_name, url=author_url)
  elif author_name is not MISSING and author_name is not None and author_icon is not MISSING and author_icon is not None:
    r.set_author(name=author_name, icon_url=author_icon)
  elif author_name is not MISSING and author_name is not None:
    r.set_author(name=author_name)
  elif author_name is MISSING and author_name is not None and (author_url is not MISSING or author_icon is not MISSING):
    raise TypeError("author_name needs to be set")

  if url is not MISSING and url is not None:
    r.url = url

  if footer is not MISSING and footer is not None:
    if footer_icon:
      r.set_footer(text=footer, icon_url=footer_icon)
    else:
      r.set_footer(text=footer)
  elif ctx is not MISSING and ctx is not None:
    r.set_footer(text="Called by: {}".format(ctx.author.display_name), icon_url=ctx.author.avatar.url)

  return r
