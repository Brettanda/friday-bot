import os

from .messagecolors import MessageColors
from . import exceptions, checks, config  # , queryIntents  # , queryGen
from .myembed import embed
from . import cache
from . import db
from .custom_contexts import MyContext  # , FakeInteractionMessage  # , MySlashContext
from .reply import msg_reply
from . import time
from .relay import relay_info
from .build_da_docs import build as build_docs
from . import views

dev_guilds = [243159711237537802, 707441352367013899, 215346091321720832]

modules = [mod[:-3] for mod in os.listdir("./functions") if mod.endswith(".py") and mod != "__init__.py" and mod != "queryGen.py" and mod != "queryIntents.py"]


__all__ = (
    "MessageColors",
    "views",
    "db",
    "cache",
    "FakeInteractionMessage",
    "build_docs",
    "config",
    "MyContext",
    "msg_reply",
    "MySlashContext",
    "relay_info",
    "exceptions",
    "get_reddit_post",
    "embed",
    "checks",
    "time",
)
