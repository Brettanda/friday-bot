import os,discord,logging

async def relay_info(msg:str,bot,embed:discord.Embed=None,file=None,short:str=None,channel:int=808594696904769546):
  log_info = bot.get_channel(channel)
  if log_info is not None:
    if file is not None:
      thispath = os.getcwd()
      if "\\" in thispath:
        seperator = "\\\\"
      else:
        seperator = "/"
      await log_info.send(content=msg,embed=embed,file=discord.File(fp=f"{thispath}{seperator}{file}",filename="Error.txt"))
    else:
      await log_info.send(content=msg,embed=embed)
  else:
    appinfo = await bot.application_info()
    owner = bot.get_user(appinfo.team.owner.id)
    if owner is not None:
      if file is not None:
        thispath = os.getcwd()
        if "\\" in thispath:
          seperator = "\\\\"
        else:
          seperator = "/"
        await owner.send(content=msg,embed=embed,file=discord.File(fp=f"{thispath}{seperator}{file}",filename="Error.txt"))
      else:
        await owner.send(content=msg,embed=embed)
  if short is not None:
    print(short)
    logging.info(short)
  else:
    print(msg)
    logging.info(msg)