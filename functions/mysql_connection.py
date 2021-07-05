import os
import sys

import mysql.connector
from mysql.connector import errors
import mysql.connector.pooling
from . import config


# def mydb_connect() -> mysql.connector.MySQLConnection():
def mydb_connect():  # -> mysql.connector.pooling.MySQLConnectionPool():
  # https://www.mysqltutorial.org/python-connecting-mysql-databases/
  if len(sys.argv) > 1 and (sys.argv[1] == "--prod" or sys.argv[1] == "--production"):
    # POOLNAME = "PROD"
    HOST = "127.0.0.1"
    USERNAME = os.getenv("DBUSERPROD")
    PASSWORD = os.getenv("DBPASSPROD")
    DATABASE = os.getenv("DATABASE")
  elif len(sys.argv) > 1 and sys.argv[1] == "--canary":
    # POOLNAME = "CAN"
    HOST = os.getenv("DBHOST")
    USERNAME = os.getenv("DBUSER")
    PASSWORD = os.getenv("DBPASS")
    DATABASE = os.getenv("DATABASECANARY")
  else:
    # POOLNAME = "TEST"
    HOST = os.getenv("DBHOST")
    USERNAME = os.getenv("DBUSER")
    PASSWORD = os.getenv("DBPASS")
    DATABASE = os.getenv("DATABASETEST")
  mydb = mysql.connector.MySQLConnection(
      # pool_name=POOLNAME,
      # pool_size=5,
      # pool_reset_session=True,
      host=HOST,
      user=USERNAME,
      password=PASSWORD,
      database=DATABASE
  )

  return mydb


# async def query(mydb: mysql.connector.MySQLConnection(), query: str, *params, rlist: bool = False) -> str or list:
async def query(mydb, query: str, *params, rlist: bool = False) -> str or list:
  try:
    mydb = mydb_connect()
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
    if "select" in query.lower():
      return result
  except errors.Error as e:
    print("MySQL Error ", e)
  finally:
    if mydb.is_connected():
      mycursor.close()
      mydb.close()


def non_coro_query(mydb, query: str, *params, rlist: bool = False) -> str or list:
  """Meant to placed in __init__() of cogs"""
  try:
    mydb = mydb_connect()
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
    if mydb.is_connected():
      mycursor.close()
      mydb.close()


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
