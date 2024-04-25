import glob
import os
from cogs.help import syntax, get_examples
from typing import TYPE_CHECKING
from discord.ext import commands

if TYPE_CHECKING:
  from index import Friday


def write_command(f: glob.glob, com: commands.Command, step: int = 0) -> None:  # type: ignore
  f.write(f"\n##{''.join('#' for x in range(step))} {com.name.capitalize()}\n")
  usage = '\n\t'.join(syntax(com, quotes=False).split('\n'))
  f.write("\n" + (com.help + "\n") if com.help is not None else '')
  slash = True if hasattr(com.cog, "slash_" + com.qualified_name) or hasattr(com.cog, "_slash_" + com.qualified_name) else False
  if (com.extras and "permissions" in com.extras) or (hasattr(com.cog, "extras") and "permissions" in com.cog.extras):
    perms = [*(com.cog.extras.get("permissions", []) if hasattr(com.cog, "extras") else []), *com.extras.get("permissions", [])]
    f.write("""\n!!! warning "Required Permission(s)"\n\t- """ + "\n\t- ".join(perms) + "\n")
  f.write(f"""\n??? {'missing' if not slash else 'check'} "{'Has' if slash else 'Does not have'} a slash command to match"\n\tLearn more about [slash commands](/#slash-commands)\n""")
  f.write(f"""\n=== "Usage"\n\t```md\n\t{usage}\n\t```\n""")
  if len(com.aliases) > 0:
    f.write("""\n=== "Aliases"\n\t```md\n\t""" + (",".join(com.aliases) if len(com.aliases) > 0 else 'None') + """\n\t```\n""")
  examples = get_examples(com, "!")
  if len(examples) > 0:
    examples = "\n\t".join(examples) if len(examples) > 0 else None
    f.write(f"""\n=== "Examples"\n\t```md\n\t{examples}\n\t```\n""")


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
  # # for f in glob.glob(f"{thispath}{seperator}docs{seperator}docs{seperator}commands{seperator}*"):
  # #   os.remove(f)
  # cogs = sorted(cogs, key=lambda x: x.qualified_name)
  # # for cog in cogs:
  # #   category = hasattr(cog, "category") and cog.category or "Commands"
  # #   for f in glob.glob(f"{thispath}{seperator}docs{seperator}docs{seperator}{category.lower()}{seperator}*"):
  # #     os.remove(f)
  # for cog in cogs:
  #   category = hasattr(cog, "category") and cog.category or "Commands"
  #   cog_name = cog.qualified_name
  #   filename = "index" if cog_name.lower() == category.lower() else cog_name.lower().replace(' ','_')
  #   path = f"docs/docs/{category.lower()}/{filename}.md"
  #   # path = f"docs/docs/commands/{cog_name.lower().replace(' ','_')}.md"
  #   try:
  #     open(path, "r").close()
  #   except FileNotFoundError:
  #     os.makedirs(f"docs/docs/{category.lower()}", exist_ok=True)

  #   with open(path, "w") as f:
  for f in glob.glob(f"{thispath}{seperator}docs{seperator}docs{seperator}commands{seperator}*"):
    os.remove(f)
  for cog in sorted(cogs, key=lambda x: x.qualified_name):
    cog_name = cog.qualified_name
    with open(f"docs/docs/commands/{cog_name.lower().replace(' ','_')}.md", "w") as f:
      # desc = cog.description and " ".join("\\n".join(cog.description.split("\n\n")).split("\n"))
      desc = cog.description and cog.description.split('\n', 1)[0]
      f.write(f"---\ntitle: {cog_name.capitalize()}\n{('description: '+desc) if desc and desc != '' else ''}\n---\n")
      f.write(f"# {cog_name.capitalize()}\n\n{cog.description}\n")
      for com in sorted(commands, key=lambda x: x.name):
        if com.hidden is False and com.enabled is True and com.cog_name == cog_name:
          f.write(f"\n## {com.name.capitalize()}\n")
          usage = '\n\t'.join(syntax(com, quotes=False).split('\n'))
          # usage = discord.utils.escape_markdown(usage)  # .replace("<", "\\<")
          f.write("\n" + (com.help + "\n") if com.help is not None else '')
          # f.write(f"""\n\n!!! example "Usage"\n\n    ```md\n    {usage}\n    ```\n\n""")
          # f.write("""\n\n!!! example "Aliases"\n\n    ```md\n    """ + (",".join(com.aliases) if len(com.aliases) > 0 else 'None') + """\n    ```\n\n""")
          slash = True if hasattr(com.cog, "slash_" + com.qualified_name) or hasattr(com.cog, "_slash_" + com.qualified_name) else False
          # TODO: add docs requirements f.write(f"""\nRequired Permissions: {', '.join([str(i) for i in com.checks])}""")
          # if (com.extras and "permissions" in com.extras) or (hasattr(com.cog, "extras") and "permissions" in com.cog.extras):
          #   perms = [*(com.cog.extras.get("permissions", []) if hasattr(com.cog, "extras") else []), *com.extras.get("permissions", [])]
          #   f.write("""\n!!! warning "Required Permission(s)"\n\t- """ + "\n\t- ".join(perms) + "\n")
          f.write(f"""\n??? {'missing' if not slash else 'check'} "{'Has' if slash else 'Does not have'} a slash command to match"\n\tLearn more about [slash commands](/#slash-commands)\n""")
          f.write(f"""\n=== "Usage"\n\t```md\n\t{usage}\n\t```\n""")
          if len(com.aliases) > 0:
            f.write("""\n=== "Aliases"\n\t```md\n\t""" + (",".join(com.aliases) if len(com.aliases) > 0 else 'None') + """\n\t```\n""")
          examples = get_examples(com, "!")
          if len(examples) > 0:
            examples = "\n\t".join(examples) if len(examples) > 0 else None
            f.write(f"""\n=== "Examples"\n\t```md\n\t{examples}\n\t```\n""")
          if hasattr(com, "commands"):
            # This is a command group
            for c in sorted(com.commands, key=lambda x: x.name):  # type: ignore
              if c.hidden is False and c.enabled is True:
                f.write(f"\n### {c.name.capitalize()}\n")
                slash = True if hasattr(c.cog, "slash_" + c.qualified_name) or hasattr(c.cog, "_slash_" + c.qualified_name) else False
                usage = '\n\t'.join(syntax(c, quotes=False).split('\n'))
                # usage = discord.utils.escape_markdown(usage)  # .replace("<", "\\<")
                # TODO: add docs requirements f.write(f"""\nRequired Permissions: {', '.join(b)}""")
                # if (c.extras and "permissions" in c.extras) or (hasattr(c.cog, "extras") and "permissions" in c.cog.extras):
                #   perms = [*(c.cog.extras.get("permissions", []) if hasattr(c.cog, "extras") else []), *c.extras.get("permissions", [])]
                #   f.write("""\n!!! warning "Required Permission(s)"\n\t- """ + "\n\t- ".join(perms) + "\n")
                f.write(f"""\n??? {'missing' if not slash else 'check'} "{'Has' if slash else 'Does not have'} a slash command to match"\n\tLearn more about [slash commands](/#slash-commands)\n""")
                f.write("\n" + (c.help + "\n") if c.help is not None else '')
                f.write(f"""\n=== "Usage"\n\n\t```md\n\t{usage}\n\t```\n""")
                if len(c.aliases) > 0:
                  f.write("""\n=== "Aliases"\n\n\t```md\n\t""" + (",".join(c.aliases) if len(c.aliases) > 0 else 'None') + "\n\t```\n")
                examples = get_examples(c, "!")
                if len(examples) > 0:
                  examples = "\n\t".join(examples) if len(examples) > 0 else None
                  f.write(f"""\n=== "Examples"\n\n\t```md\n\t{examples}\n\t```\n""")
          # write_command(f, com)
          # if hasattr(com, "commands"):
          #   for c in sorted(com.commands, key=lambda x: x.name):
          #     if c.hidden is False and c.enabled is True:
          #       write_command(f, c, step=1)
          #       if hasattr(c, "commands"):
          #         for c in sorted(c.commands, key=lambda x: x.name):
          #           if c.hidden is False and c.enabled is True:
          #             write_command(f, c, step=2)
          #             if hasattr(c, "commands"):
          #               for c in sorted(c.commands, key=lambda x: x.name):
          #                 if c.hidden is False and c.enabled is True:
          #                   write_command(f, c, step=3)
      f.close()
