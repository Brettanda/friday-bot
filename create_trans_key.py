import json
import os

from dotenv import load_dotenv

load_dotenv()


def run():
  with open("friday-trans-key.json", "w") as key:
    content = {
        "type": "service_account",
        "project_id": os.environ.get("PROJECT_ID"),
        "private_key_id": os.environ.get("PRIVATE_KEY_ID"),
        "private_key": os.environ.get("PRIVATE_KEY"),
        "client_email": os.environ.get("CLIENT_EMAIL"),
        "client_id": os.environ.get("CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.environ.get("CLIENT_CERT_URL")
    }

    key.write(json.dumps(content, ensure_ascii=True, indent=2))
    key.close()


if __name__ == "__main__":
  run()
