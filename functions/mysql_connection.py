import mysql.connector,os,sys
from discord.ext import commands

# class MySQL():
#   def __init__(self):
#     True

def mydb_connect():
  # https://www.mysqltutorial.org/python-connecting-mysql-databases/
  if len(sys.argv) > 1 and (sys.argv[1] == "--prod" or sys.argv[1] == "--production"):
    DATABASE = os.getenv("DATABASE")
  else:
    DATABASE = os.getenv("DATABASETEST")
  mydb = mysql.connector.connect(
    host=os.getenv("DBHOST"),
    user=os.getenv("DBUSER"),
    password=os.getenv("DBPASS"),
    database=DATABASE
  )

  return mydb

def query(mydb,query:str,*params):
  # print(params)
  mydb = mydb_connect()
  mycursor = mydb.cursor(prepared=True)
  mycursor.execute(query,params)
  if "select" in query.lower():
    if "where" in query.lower():
      result = mycursor.fetchone()[0]
    else:
      result = mycursor.fetchall()
  mydb.commit()
  mydb.close()
  if "select" in query.lower():
    return result

def query_prefix(bot,ctx,client:bool=False):
  try:
    if str(ctx.channel.type) == "private":
      return commands.when_mentioned_or("!")(bot,ctx)
    mydb = mydb_connect()
    mycursor = mydb.cursor()
    mycursor.execute(f"SELECT prefix FROM servers WHERE id='{ctx.guild.id}'")

    result = mycursor.fetchall()
    mydb.commit()
    mydb.close()

    if client == True:
      return result[0][0]
    else:
      try:
        return commands.when_mentioned_or(result[0][0] or "!")(bot,ctx)
      except:
        return commands.when_mentioned_or("!")(bot,ctx)
    # return commands.when_mentioned_or("!")(bot,ctx)
    # return "!"
  except:
    raise
  return "!"