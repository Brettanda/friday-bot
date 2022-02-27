import os

ignore = [
    "log.py",
    "__init__.py",
    "database.py",
]

default = [
    com[:-3] for com in os.listdir("./cogs")
    if com.endswith(".py") and com not in ignore
]

try:
  spice = [
      com[:-3] for com in os.listdir("./spice/cogs")
      if com.endswith(".py") and com not in ignore
  ]
except FileNotFoundError:
  spice = []

__all__ = (
    "default",
    "spice",
)
