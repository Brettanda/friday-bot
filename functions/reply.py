from discord import Forbidden, HTTPException


async def msg_reply(message, content=None, **kwargs):
  if not hasattr(kwargs, "mention_author"):
    kwargs.update({"mention_author": False})
  try:
    return await message.reply(content, **kwargs)
  except Forbidden as e:
    if "Cannot reply without permission" in str(e):
      try:
        return await message.channel.send(content, **kwargs)
      except Exception:
        pass
    elif "Missing Permissions" in str(e):
      pass
    else:
      raise e
  except HTTPException as e:
    if "Unknown message" in str(e):
      try:
        return await message.channel.send(content, **kwargs)
      except Exception:
        pass
    else:
      raise e
