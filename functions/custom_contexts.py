from discord_slash import SlashContext
from discord.ext.commands import Context
import discord


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


class MyContext(Context):
  async def reply(self, content=None, **kwargs):
    ignore_coms = ["log", "help", "meme", "issue", "reactionrole", "minesweeper", "poll", "confirm", "souptime", "say"]
    if not hasattr(kwargs, "delete_after") and self.command is not None and self.command.name not in ignore_coms:
      if hasattr(self.bot, "get_guild_delete_commands"):
        delete = self.bot.get_guild_delete_commands(self.message.guild)
      else:
        delete = None
      delete = delete if delete is not None and delete != 0 else None
      if delete is not None:
        kwargs.update({"delete_after": delete})
        await self.message.delete(delay=delete)
    if not hasattr(kwargs, "mention_author"):
      kwargs.update({"mention_author": False})
    try:
      return await self.message.reply(content, **kwargs)
    except discord.Forbidden as e:
      if "Cannot reply without permission" in str(e):
        try:
          return await self.message.channel.send(content, **kwargs)
        except Exception:
          pass
      elif "Missing Permissions" in str(e):
        pass
      else:
        raise e
    except discord.HTTPException as e:
      if "Unknown message" in str(e):
        try:
          return await self.message.channel.send(content, **kwargs)
        except Exception:
          pass
      else:
        raise e
