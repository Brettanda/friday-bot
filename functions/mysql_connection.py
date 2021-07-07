
from mysql.connector import errors
import sqlite3
from . import config


# def mydb_connect() -> mysql.connector.MySQLConnection():
def mydb_connect() -> sqlite3.Connection:  # -> mysql.connector.pooling.MySQLConnectionPool():
  # https://www.mysqltutorial.org/python-connecting-mysql-databases/
  # mydb = sqlite3.connect("friday.db")

  # return mydb
  return None


# async def query(mydb: mysql.connector.MySQLConnection(), query: str, *params, rlist: bool = False) -> str or list:
async def query(mydb: sqlite3.Connection, query: str, *params, rlist: bool = False) -> str or list:
  try:
    mydb = sqlite3.connect("friday.db")
    mydb = mydb_connect()
    mycursor = mydb.cursor()
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
    # if not mydb.is_connected():
    #   mydb.reconnect(attempts=2, delay=0.1)
    mydb.commit()
    if "select" in query.lower():
      return result
  except errors.Error as e:
    print("MySQL Error ", e)
  finally:
    mycursor.close()
    mydb.close()
  #   if mydb.is_connected():


def non_coro_query(mydb: sqlite3.Connection, query: str, *params, rlist: bool = False) -> str or list:
  """Meant to placed in __init__() of cogs"""
  try:
    mydb = sqlite3.connect("friday.db")
    # if not mydb.is_connected():
    #   mydb.reconnect(attempts=2, delay=0.1)
    mycursor = mydb.cursor()
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
    # if not mydb.is_connected():
    #   mydb.reconnect(attempts=2, delay=0.1)
    mydb.commit()
    # mycursor.close()
    if "select" in query.lower():
      return result
  except errors.Error as e:
    print("MySQL Error ", e)
  finally:
    mycursor.close()
    mydb.close()
  #   if mydb.is_connected():


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
