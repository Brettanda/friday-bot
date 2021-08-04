import os

from .messagecolors import MessageColors
from .mysql_connection import mydb_connect, query, non_coro_query
from . import exceptions, checks, config  # , queryIntents  # , queryGen
from .myembed import embed

from .custom_contexts import MyContext, MySlashContext, FakeInteractionMessage
from .custom_pages import Menu
from .reply import msg_reply
from .time import timeit
from .relay import relay_info
from .reddit_post import get_reddit_post
from .build_da_docs import build as build_docs
from . import views
dev_guilds = [243159711237537802, 707441352367013899, 215346091321720832]

modules = [mod[:-3] for mod in os.listdir("./functions") if mod.endswith(".py") and mod != "__init__.py" and mod != "queryGen.py" and mod != "queryIntents.py"]

__all__ = ["MessageColors", "views", "FakeInteractionMessage", "build_docs", "Menu", "config", "MyContext", "msg_reply", "MySlashContext", "timeit", "relay_info", "exceptions", "get_reddit_post", "mydb_connect", "query", "non_coro_query", "embed", "checks"]
