import asyncio
import logging
import os
import glob

from dotenv import load_dotenv
from cogs.help import syntax

from index import Friday

# from create_trans_key import run

load_dotenv(dotenv_path="./.env")
TOKEN = os.environ.get('TOKENTEST')


async def build(bot: "Friday", prefix: str = "!"):
  commands = bot.commands
  cogs = []
  for command in commands:
    if command.hidden is False and command.enabled is True and command.cog_name not in cogs:
      cogs.append(command.cog)
  thispath = os.getcwd()
  if "\\" in thispath:
    seperator = "\\\\"
  else:
    seperator = "/"
  for f in glob.glob(f"{thispath}{seperator}docs{seperator}commands{seperator}*"):
    os.remove(f)
  for cog in cogs:
    cog_name = cog.qualified_name
    with open(f"docs/commands/{cog_name.lower().replace(' ','_')}.md", "w") as f:
      f.write(f"# {cog_name.capitalize()}\n\n{cog.description}\n\n")
      for com in commands:
        if com.hidden is False and com.enabled is True and com.cog_name == cog_name:
          f.write(f"## {com.name.capitalize()}\n\n")
          usage = '\n'.join(syntax(com, quotes=False).split('\n'))
          # usage = discord.utils.escape_markdown(usage)  # .replace("<", "\\<")
          f.write(f"{com.description or ''}\n\n")
          f.write(f"""Usage:\n\n```md\n{usage}\n```\n\n""")
          f.write("Aliases:\n\n```md\n" + (",".join(com.aliases) if len(com.aliases) > 0 else 'None') + "\n```\n\n")
          if hasattr(com, "commands"):
            # This is a command group
            for c in com.commands:
              f.write(f"### {c.name.capitalize()}\n")
              usage = '\n'.join(syntax(c, quotes=False).split('\n'))
              # usage = discord.utils.escape_markdown(usage)  # .replace("<", "\\<")
              f.write(f"{c.description or ''}\n")
              f.write(f"""Usage:\n\n```none\n{usage}\n```\n\n""")
              f.write("Aliases:\n\n```none\n" + (",".join(c.aliases) if len(c.aliases) > 0 else 'None') + "\n```\n\n")
      f.close()


class Friday_testing(Friday):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

  async def on_ready(self):
    await build(self, "!")
    await asyncio.sleep(2)
    await self.close()

# TODO: Add a check for functions modules/files not being named the same as the functions/defs


# def test_translate_key_gen():
#   run()
if __name__ == "__main__":
  bot = Friday_testing()
  loop = asyncio.get_event_loop()
  try:
    loop.run_until_complete(bot.start(TOKEN, bot=True))
  except KeyboardInterrupt:
    # mydb.close()
    logging.info("STOPED")
    loop.run_until_complete(bot.close())
  finally:
    loop.close()
