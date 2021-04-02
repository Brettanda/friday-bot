from discord_slash import SlashContext
from discord.ext.commands import Context


class MySlashContext(SlashContext):
  def __init__(self):
    self.reply = self.reply

  async def reply(self, content=None, **kwargs):
    await self.send(content, **kwargs)
    # if not hasattr(kwargs,"delete_after") and self.command.name not in ["meme","issue","reactionrole","minesweeper"]:
    #   delete = await get_delete_time(self)
    #   delete = delete if delete is not None and delete != 0 else None
    #   if delete != None:
    #     kwargs.update({"delete_after":delete})
    #     await self.message.delete(delay=delete)
    # try:
    #   return await self.message.reply(content,**kwargs)
    # except discord.Forbidden as e:
    #   if "Cannot reply without permission" in str(e):
    #     return await self.message.channel.send(content,**kwargs)
    #   else:
    #     raise e
    # except discord.HTTPException as e:
    #   if "Unknown message" in str(e):
    #     return await self.message.channel.send(content,**kwargs)
    #   else:
    #     raise e
