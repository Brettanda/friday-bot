import os

default = [
    com[:-3] for com in os.listdir("./cogs")
    if com.endswith(".py") and com != "__init__.py" and com != "log.py" and com != "database.py"
]

try:
  spice = [
      com[:-3] for com in os.listdir("./spice/cogs")
      if com.endswith(".py") and com != "__init__.py" and com != "log.py" and com != "database.py"
  ]
except FileNotFoundError:
  spice = []

__all__ = (
    "default",
    "spice",
)
