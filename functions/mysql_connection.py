# Move to PostgreSQL when bot get big

from mysql.connector import errors
import asqlite
import sqlite3
# from . import config

from typing import Union

# def mydb_connect() -> mysql.connector.MySQLConnection():
async def mydb_connect() -> asqlite.Connection:  # -> mysql.connector.pooling.MySQLConnectionPool():
  # https://www.mysqltutorial.org/python-connecting-mysql-databases/
  # mydb = sqlite3.connect("friday.db")

  # return mydb
  return None


# async def query(mydb: mysql.connector.MySQLConnection(), query: str, *params, rlist: bool = False) -> str or list:
async def query(mydb: asqlite.Connection, query: str, *params, rlist: bool = False) -> Union[str, list]:
  async with asqlite.connect("friday.db") as mydb:
    async with mydb.cursor() as mycursor:
      await mycursor.execute(query, params)
      if "select" in query.lower():
        if "where" in query.lower() and "," not in query.lower() and '>' not in query.lower().split("where")[1] and '<' not in query.lower().split("where")[1] or "limit" in query.lower():
          if rlist is True:
            result = await mycursor.fetchall()
          else:
            result = await mycursor.fetchone()
            result = result[0] if result is not None else None
        else:
          result = await mycursor.fetchall()
      else:
        await mydb.commit()
      if "select" in query.lower():
        return result


def non_coro_query(mydb: sqlite3.Connection, query: str, *params, rlist: bool = False) -> Union[str, list]:
  """Meant to placed in __init__() of cogs"""
  try:
    mydb = sqlite3.connect("friday.db", 30.0)
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
