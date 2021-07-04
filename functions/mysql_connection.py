import os
import sys

import mysql.connector
from . import config


def mydb_connect() -> mysql.connector.MySQLConnection():
  # https://www.mysqltutorial.org/python-connecting-mysql-databases/
  if len(sys.argv) > 1 and (sys.argv[1] == "--prod" or sys.argv[1] == "--production"):
    DATABASE = os.getenv("DATABASE")
  elif len(sys.argv) > 1 and sys.argv[1] == "--canary":
    DATABASE = os.getenv("DATABASECANARY")
  else:
    DATABASE = os.getenv("DATABASETEST")
  mydb = mysql.connector.connect(
      host=os.getenv("DBHOST"),
      user=os.getenv("DBUSER"),
      password=os.getenv("DBPASS"),
      database=DATABASE
  )

  return mydb


async def query(mydb: mysql.connector.MySQLConnection(), query: str, *params, rlist: bool = False) -> str or list:
  if not mydb.is_connected():
    mysql.reconnect(attempts=10, delay=1)
  mycursor = mydb.cursor(prepared=True)
  mycursor.execute(query, params)
  if "select" in query.lower():
    if "where" in query.lower() and "," not in query.lower() and '>' not in query.lower().split("where")[1] and '<' not in query.lower().split("where")[1] or "limit" in query.lower():
      if rlist is True:
        result = mycursor.fetchall()
      else:
        result = mycursor.fetchone()
        result = result[0] if result is not None else None
    else:
      result = mycursor.fetchall()
  mydb.commit()
  if not mydb.is_connected():
    mysql.reconnect(attempts=10, delay=1)
  if "select" in query.lower():
    return result


def non_coro_query(mydb, query: str, *params, rlist: bool = False) -> str or list:
  """Meant to placed in __init__() of cogs"""
  mycursor = mydb.cursor(prepared=True)
  mycursor.execute(query, params)
  if "select" in query.lower():
    if "where" in query.lower() and "," not in query.lower() and '>' not in query.lower().split("where")[1] and '<' not in query.lower().split("where")[1] or "limit" in query.lower():
      if rlist is True:
        result = mycursor.fetchall()
      else:
        result = mycursor.fetchone()
        result = result[0] if result is not None else None
    else:
      result = mycursor.fetchall()
  mydb.commit()
  if "select" in query.lower():
    return result


async def query_prefix(bot, ctx, client: bool = False) -> str:
  if str(ctx.channel.type) == "private":
    return config.defaultPrefix

  mycursor = bot.log.mydb.cursor()
  mycursor.execute(f"SELECT prefix FROM servers WHERE id='{ctx.guild.id}'")

  result = mycursor.fetchall()
  try:
    bot.log.mydb.commit()
  except BaseException:
    pass

  if client is True:
    return result[0][0]
  else:
    try:
      return result[0][0] or config.defaultPrefix
    except BaseException:
      return config.defaultPrefix

  return config.defaultPrefix
