#!/usr/bin/env bash
# Restart the lab server of the workbench (pipeline/lab_server.py, port 8168).
#
# Usage: scripts/restart_lab_server.sh [--dry-run]
# The script runs from any directory. The server runs in the workbench root.
#
# 1. Checks: the listener on port 8168 is pipeline/lab_server.py of this workbench.
#    config.yaml and the schema version of the database pass the start check of the
#    server. A failed check stops the script before it stops the server.
# 2. Stop with SIGTERM (rule 23 of CLAUDE.md). The server stops its image description
#    watcher before it exits. The script never sends SIGKILL.
# 3. Start `python3 pipeline/lab_server.py --no-browser` in its own session, with the
#    log in work/lab_server.log. Wait until GET /api/dataset answers HTTP 200.
# When no server runs, the script only starts it.
set -euo pipefail

WB="$(cd "$(dirname "$0")/.." && pwd -P)"
PORT=8168
URL="http://127.0.0.1:$PORT"
LOGFILE="$WB/work/lab_server.log"
STOP_TIMEOUT=30   # The server waits up to 10 s for the watcher.
START_TIMEOUT=60

usage() {
  sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
}

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }

DRY_RUN=0
for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

# Plain lsof takes 15-50 s on this Mac. -b skips the blocking stat calls.
listener_pids() { lsof -bnPw -t -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true; }

# Succeed when pid $1 runs pipeline/lab_server.py of this workbench.
is_lab_server() {
  local pid=$1 cmd cwd
  cmd=$(ps -o command= -p "$pid" 2>/dev/null) || return 1
  [[ $cmd == *pipeline/lab_server.py* ]] || return 1
  [[ $cmd == *"$WB/pipeline/lab_server.py"* ]] && return 0
  cwd=$(lsof -bnPw -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')
  [[ $cwd == "$WB" ]]
}

any_alive() {
  local pid
  for pid in "$@"; do kill -0 "$pid" 2>/dev/null && return 0; done
  return 1
}

http_code() { curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$URL/api/dataset" || true; }

# The start check of lab_server.main: read config.yaml, open the database, and compare
# its schema version with pipeline/schema/.
start_check() {
  (cd "$WB" && python3 - <<'PY'
import sqlite3
import sys
from contextlib import closing

sys.path.insert(0, "pipeline")
import lab_server

try:
    config, db_path = lab_server.read_config(lab_server.CONFIG_PATH)
    with closing(lab_server.open_database(db_path)) as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
except (lab_server.ConfigError, sqlite3.Error) as exc:
    print("error: %s" % exc, file=sys.stderr)
    sys.exit(1)
print("database %s, schema version %d" % (db_path, version))
PY
  )
}

# ---------------------------------------------------------------- checks

PIDS=""
for pid in $(listener_pids); do
  is_lab_server "$pid" ||
    die "port $PORT belongs to pid $pid ($(ps -o command= -p "$pid" | cut -c1-120)), not to the lab server of $WB"
  PIDS+="$pid "
done
PIDS=$(echo $PIDS)

if [[ -n $PIDS ]]; then
  log "lab server: running, pid $PIDS, started $(ps -o lstart= -p "${PIDS%% *}" | sed 's/ *$//')"
else
  log "lab server: not running"
fi

CHECK=$(start_check) ||
  die "the server would not start with this config.yaml and database. Nothing was stopped."
log "start check: $CHECK"

if ((DRY_RUN)); then
  log "dry run: nothing was stopped or started"
  exit 0
fi

# ---------------------------------------------------------------- stop

if [[ -n $PIDS ]]; then
  log "SIGTERM to pid $PIDS (wait up to ${STOP_TIMEOUT} s)"
  kill -TERM $PIDS 2>/dev/null || true
  start=$SECONDS
  while any_alive $PIDS; do
    ((SECONDS - start < STOP_TIMEOUT)) ||
      die "pid $PIDS still runs after ${STOP_TIMEOUT} s. Stop it by hand, then run the script again."
    sleep 1
  done
  log "stopped"
fi

pids=$(listener_pids)
[[ -z $pids ]] || die "port $PORT is still in use by pid $(echo $pids)"

# ---------------------------------------------------------------- start

# start_new_session=True: a server in the process group of the calling shell can die
# when that shell ends (seen on 2026-09-25 with `nohup ... &`).
mkdir -p "$(dirname "$LOGFILE")"
printf '\n===== %s restart_lab_server.sh start\n' "$(date '+%Y-%m-%d %H:%M:%S')" >>"$LOGFILE"
NEW=$(cd "$WB" && python3 - "$LOGFILE" <<'PY'
import subprocess
import sys

with open(sys.argv[1], "ab", buffering=0) as output:
    process = subprocess.Popen(
        ["python3", "pipeline/lab_server.py", "--no-browser"],
        stdin=subprocess.DEVNULL,
        stdout=output,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )
print(process.pid)
PY
)
log "started pid $NEW, log $LOGFILE"

start=$SECONDS
until [[ $(http_code) == 200 ]]; do
  if ! kill -0 "$NEW" 2>/dev/null; then
    log "the server exited during start. Last lines of $LOGFILE:" >&2
    tail -n 20 "$LOGFILE" >&2
    exit 1
  fi
  ((SECONDS - start < START_TIMEOUT)) ||
    die "no HTTP 200 from $URL/api/dataset after ${START_TIMEOUT} s. See $LOGFILE"
  sleep 1
done

log "ready: $URL/dataset, pid $NEW, pgid $(ps -o pgid= -p "$NEW" | tr -d ' ')"
