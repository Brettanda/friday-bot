import os

from dotenv import load_dotenv

load_dotenv()

with open("friday.sql", "w") as f:
  f.write(os.environ.get("DB_FILE"))
  f.close()
