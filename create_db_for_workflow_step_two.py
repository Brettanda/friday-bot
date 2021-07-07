import sqlite3

from dotenv import load_dotenv

load_dotenv()


def run():
  db = sqlite3.connect("friday.db")
  sql_file = open("friday.sqlite", encoding="utf-8")
  print(sql_file)
  cur = db.cursor()
  # try:
  string = sql_file.read().encode("utf8")
  print(string)
  cur.executescript(string)
  db.commit()
  # except Exception:
  #   pass
  # for row in cur.execute("SELECT * FROM servers LIMIT 10"):
  #   print(row)
  cur.close()
  db.close()


if __name__ == "__main__":
  run()
