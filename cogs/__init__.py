import os

default = [com[:-3] for com in os.listdir("./cogs") if com.endswith(".py") and com != "__init__.py" and com != "log.py"]
