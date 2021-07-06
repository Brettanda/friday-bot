import os
import sqlite3

from dotenv import load_dotenv

load_dotenv()


def run():
  with open("friday.sql", "w") as f:
    f.write(os.environ.get("DB_FILE"))
    f.close()
  db = sqlite3.connect(":memory:")
  sql_file = open("friday.sql")
  cur = db.cursor()
  try:
    string = sql_file.read()
    cur.executescript(string)
    db.commit()
  except Exception:
    pass
  for row in cur.execute("SELECT * FROM servers LIMIT 10"):
    print(row)
  cur.close()
  db.close()


if __name__ == "__main__":
  run()
