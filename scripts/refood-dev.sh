#!/usr/bin/env bash
# Run with: bash scripts/refood-dev.sh
# Local-only setup: MariaDB, dedicated test DB, Python dependencies, and full tests.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
BACKEND="$ROOT/src/backend"
COMPOSE="$BACKEND/database/compose.yaml"
ENV_FILE="$BACKEND/database/.env"
EXAMPLE="$BACKEND/database/.env.example"
say() { printf '\n==> %s\n' "$*"; }
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null || die "Docker is not installed."
if [ ! -f "$ENV_FILE" ]; then
  cp "$EXAMPLE" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  say "Created local .env from template (local development credentials only)."
fi
# This is the user's own local file, not arbitrary downloaded shell input.
set -a
source "$ENV_FILE"
set +a
: "$MARIADB_DATABASE"
: "$MARIADB_USER"
: "$MARIADB_PASSWORD"
: "$MARIADB_ROOT_PASSWORD"
MARIADB_PORT="$(printf '%s' "$MARIADB_PORT")"
[[ "$MARIADB_DATABASE" =~ ^[A-Za-z0-9_]+$ ]] || die "Invalid database name"
[[ "$MARIADB_USER" =~ ^[A-Za-z0-9_]+$ ]] || die "Invalid database username"
[[ "$MARIADB_PORT" =~ ^[0-9]+$ ]] || die "Invalid database port"
TEST_DB="$MARIADB_DATABASE"_test

if docker info >/dev/null 2>&1; then
  docker_cmd() { docker "$@"; }
else
  command -v sudo >/dev/null || die "Need sudo to access Docker daemon."
  docker_cmd() { sudo docker "$@"; }
fi

say "Starting MariaDB..."
docker_cmd compose --env-file "$ENV_FILE" -f "$COMPOSE" up -d --wait
CONTAINER_ID="$(docker_cmd compose --env-file "$ENV_FILE" -f "$COMPOSE" ps -q mariadb)"
[ -n "$CONTAINER_ID" ] || die "Cannot find running MariaDB container"

say "Creating $TEST_DB and granting test-only database access..."
SQL="CREATE DATABASE IF NOT EXISTS $TEST_DB; GRANT ALL PRIVILEGES ON $TEST_DB.* TO '$MARIADB_USER'@'%';"
docker_cmd exec -e "MYSQL_PWD=$MARIADB_ROOT_PASSWORD" "$CONTAINER_ID" mariadb -uroot -e "$SQL"

if [ ! -x "$BACKEND/.venv/bin/python" ]; then
  say "Creating virtual environment..."
  python3 -m venv "$BACKEND/.venv"
fi
PYTHON="$BACKEND/.venv/bin/python"
say "Installing Python dependencies..."
"$PYTHON" -m pip install -q -r "$BACKEND/database/requirements.txt"

# Properly URL-escape local credentials before passing them to SQLAlchemy.
eval "$("$PYTHON" - <<'PY'
import os, shlex
from sqlalchemy.engine import URL
common = dict(drivername="mysql+pymysql",
              username=os.environ["MARIADB_USER"],
              password=os.environ["MARIADB_PASSWORD"],
              host="127.0.0.1", port=int(os.environ["MARIADB_PORT"]))
for variable, database in (
    ("DATABASE_URL", os.environ["MARIADB_DATABASE"]),
    ("TEST_DATABASE_URL", os.environ["MARIADB_DATABASE"] + "_test"),
):
    url = URL.create(**common, database=database).render_as_string(hide_password=False)
    print("export " + variable + "=" + shlex.quote(url))
PY
)"
cd "$BACKEND"
say "Initializing application database..."
"$PYTHON" -m database.engine
say "Running all unit + live MariaDB tests..."
# Fixture-based unit tests must not read the persistent application catalog.
# TEST_DATABASE_URL remains set so the opt-in MariaDB test still runs.
env -u DATABASE_URL "$PYTHON" -m unittest discover -s tests -v
say "Success. Both databases are ready."
printf '\nTo start Flask:\n  cd %q\n  source .venv/bin/activate\n  export DATABASE_URL=%q\n  python app.py\n' "$BACKEND" "$DATABASE_URL"
