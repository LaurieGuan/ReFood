"""Local-only, interactive first-run .env setup for direct `python app.py` launches.

No prompts on tests, imports, CI, or non-interactive terminals.
"""
import getpass
import os
import sys
from pathlib import Path
from urllib.parse import quote

from dotenv import dotenv_values, load_dotenv

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"


def configure_local_environment():
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=False)
        return

    if not sys.stdin.isatty():
        # CI and service managers should provide env vars directly.
        return

    print("\nREFOOD local first-run setup. This writes src/backend/.env (gitignored).")
    print("Enter a Gemini key for real fridge scanning, or leave blank to configure later.")
    key = getpass.getpass("Gemini API key (hidden, Enter to skip): ").strip()
    template = [
        "FLASK_APP=app:create_app",
        "FLASK_DEBUG=0",
        "CORS_ORIGINS=*",
        "VISION_API_URL=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "VISION_MODEL=gemini-3-flash-preview",
    ]
    if key:
        # Quote safely for python-dotenv; never print the secret.
        escaped = key.replace("\\", "\\\\").replace('"', '\\"')
        template.append('VISION_API_KEY="' + escaped + '"')
    else:
        template.append("VISION_API_KEY=")

    # Reuse existing local Docker credentials if available; no hardcoded passwords.
    db_path = ROOT / "database" / ".env"
    db = dotenv_values(db_path) if db_path.exists() else {}
    if db.get("MARIADB_USER") and db.get("MARIADB_PASSWORD") and db.get("MARIADB_DATABASE"):
        user = quote(db["MARIADB_USER"], safe="")
        password = quote(db["MARIADB_PASSWORD"], safe="")
        database = quote(db["MARIADB_DATABASE"], safe="")
        port = db.get("MARIADB_PORT") or "3306"
        template.append(f"DATABASE_URL=mysql+pymysql://{user}:{password}@127.0.0.1:{port}/{database}")
        print("Found local Docker DB configuration; using MariaDB for persistence.")
    else:
        template.append("DATABASE_URL=")
        print("No database/.env found; configure DATABASE_URL later for persistence.")

    # Exclusive creation and restrictive file permissions protect the API key.
    fd = os.open(ENV_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        file.write("\n".join(template) + "\n")
    load_dotenv(ENV_PATH, override=False)
    print("Created ignored backend .env file.\n")
