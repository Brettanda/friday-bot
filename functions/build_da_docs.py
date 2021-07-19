import glob
import os
from cogs.help import syntax, get_examples
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
  for cog in sorted(cogs, key=lambda x: x.qualified_name):
    cog_name = cog.qualified_name
    with open(f"docs/commands/{cog_name.lower().replace(' ','_')}.md", "w") as f:
      f.write(f"# {cog_name.capitalize()}\n\n{cog.description}\n")
      for com in sorted(commands, key=lambda x: x.name):
        if com.hidden is False and com.enabled is True and com.cog_name == cog_name:
          f.write(f"\n## {com.name.capitalize()}\n")
          usage = "!" + '\n!'.join(syntax(com, quotes=False).split('\n'))
          # usage = discord.utils.escape_markdown(usage)  # .replace("<", "\\<")
          f.write("\n" + (com.help + "\n") if com.help is not None else '')
          # f.write(f"""\n\n!!! example "Usage"\n\n    ```md\n    {usage}\n    ```\n\n""")
          # f.write("""\n\n!!! example "Aliases"\n\n    ```md\n    """ + (",".join(com.aliases) if len(com.aliases) > 0 else 'None') + """\n    ```\n\n""")
          slash = True if hasattr(com.cog, "slash_" + com.qualified_name) or hasattr(com.cog, "_slash_" + com.qualified_name) else False
          f.write(f"""\n??? {'missing' if not slash else 'check'} "{'Has' if slash else 'Does not have'} a slash command to match"\n\tLearn more about [slash commands](/#slash-commands)\n""")
          f.write(f"""\nUsage:\n\n```md\n{usage}\n```\n""")
          if len(com.aliases) > 0:
            f.write("\nAliases:\n\n```md\n" + (",".join(com.aliases) if len(com.aliases) > 0 else 'None') + "\n```\n")
          examples = get_examples(com, "!")
          if len(examples) > 0:
            examples = "\n".join(examples) if len(examples) > 0 else None
            f.write(f"\nExamples:\n\n```md\n{examples}\n```\n")
          if hasattr(com, "commands"):
            # This is a command group
            for c in sorted(com.commands, key=lambda x: x.name):
              if c.hidden is False and c.enabled is True:
                f.write(f"\n### {c.name.capitalize()}\n")
                slash = True if hasattr(c.cog, "slash_" + c.qualified_name) or hasattr(c.cog, "_slash_" + c.qualified_name) else False
                f.write(f"""\n??? {'missing' if not slash else 'check'} "{'Has' if slash else 'Does not have'} a slash command to match"\n\tLearn more about [slash commands](/#slash-commands)\n""")
                usage = "!" + '\n!'.join(syntax(c, quotes=False).split('\n'))
                # usage = discord.utils.escape_markdown(usage)  # .replace("<", "\\<")
                f.write("\n" + (c.help + "\n") if c.help is not None else '')
                f.write(f"""\nUsage:\n\n```md\n{usage}\n```\n""")
                if len(c.aliases) > 0:
                  f.write("\nAliases:\n\n```md\n" + (",".join(c.aliases) if len(c.aliases) > 0 else 'None') + "\n```\n")
                examples = get_examples(c, "!")
                if len(examples) > 0:
                  examples = "\n".join(examples) if len(examples) > 0 else None
                  f.write(f"\nExamples:\n\n```md\n{examples}\n```\n")
      f.close()
