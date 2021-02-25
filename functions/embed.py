import discord

from functions.messagecolors import MessageColors

# class Embed():
#   def __init__(self,MessageColors):
#     self.MessageColors = MessageColors

def embed(title:str="Text",description:str="",color=None,author_name:str=None,author_url:str=None,author_icon:str=None,image:str=None,thumbnail:str=None,footer:str=None,footer_icon:str=None,ctx=None,fieldstitle:str or list=None,fieldsval:str or list=None, url:str=None):
  if color is None:
    color = MessageColors.DEFAULT
  r = discord.Embed(title=title,description=description,color=color)

  if image is not None:
    r.set_image(url=image)

  if thumbnail is not None:
    r.set_thumbnail(url=thumbnail)

  # if len(fieldstitle) > 0 and len(fieldsval) > 0:
  if fieldstitle is not None and fieldsval is not None and isinstance(fieldstitle,list) and isinstance(fieldsval,list):
    if len(fieldstitle) > 0 and len(fieldsval) > 0 and len(fieldstitle) == len(fieldsval):
      x = 0
      for i in fieldstitle:
        r.add_field(name=i,value=fieldsval[x], inline=True)
        x += 1
    else:
      raise "fieldstitle and fieldsval must have the same number of elements"
  elif isinstance(fieldstitle,str) and isinstance(fieldsval,str):
    r.add_field(name=fieldstitle,value=fieldsval)

  if author_name is not None and author_url is not None and author_icon is not None:
    r.set_author(name=author_name,url=author_url,icon_url=author_icon)
  elif author_name is not None and author_url is not None:
    r.set_author(name=author_name,url=author_url)
  elif author_name is not None and author_icon is not None:
    r.set_author(name=author_name,icon_url=author_icon)
  elif author_name is not None:
    r.set_author(name=author_name)
  elif author_name is None and (author_url is not None or author_icon is not None):
    raise "author_name needs to be set"
    return
  
  if url is not None:
    r.url = url

  if footer is not None:
    if(footer_icon):
      r.set_footer(text=footer,icon_url=footer_icon)
    else:
      r.set_footer(text=footer)
  elif ctx is not None:
    r.set_footer(text="Called by: {}".format(ctx.author.display_name),icon_url=ctx.author.avatar_url)

  return r