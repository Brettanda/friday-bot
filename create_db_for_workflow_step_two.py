import os
import sqlite3
import subprocess

from dotenv import load_dotenv

load_dotenv()


def run():
  with open("friday.sql", "w") as f:
    f.write(os.environ.get("DB_FILE"))
    f.close()
  process = subprocess.Popen("sudo ./mysqltosqlite.sh friday.sql | sqlite friday.sqlite", shell=True, stdout=subprocess.PIPE)
  process.wait()
  db = sqlite3.connect("friday.db")
  sql_file = open("friday.sqlite")
  print(sql_file)
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
