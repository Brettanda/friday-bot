import glob
import os
from cogs.help import syntax
from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
  from index import Friday


def build(bot: "Friday", prefix: str = "!"):
  commands = bot.commands
  cogs = []
  for command in commands:
    if command.hidden is False and command.enabled is True and command.cog_name not in cogs and command.cog is not None:
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
          f.write(f"{com.help or ''}\n\n")
          # f.write(f"""\n\n!!! example "Usage"\n\n    ```md\n    {usage}\n    ```\n\n""")
          # f.write("""\n\n!!! example "Aliases"\n\n    ```md\n    """ + (",".join(com.aliases) if len(com.aliases) > 0 else 'None') + """\n    ```\n\n""")
          f.write(f"""Usage:\n\n```md\n{usage}\n```\n\n""")
          f.write("Aliases:\n\n```md\n" + (",".join(com.aliases) if len(com.aliases) > 0 else 'None') + "\n```\n\n")
          if hasattr(com, "commands"):
            # This is a command group
            for c in com.commands:
              f.write(f"### {c.name.capitalize()}\n")
              usage = '\n'.join(syntax(c, quotes=False).split('\n'))
              # usage = discord.utils.escape_markdown(usage)  # .replace("<", "\\<")
              f.write(f"{c.help or ''}\n")
              f.write(f"""Usage:\n\n```none\n{usage}\n```\n\n""")
              f.write("Aliases:\n\n```none\n" + (",".join(c.aliases) if len(c.aliases) > 0 else 'None') + "\n```\n\n")
      f.close()
