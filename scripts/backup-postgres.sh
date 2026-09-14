#!/usr/bin/env bash
# Production PostgreSQL backup for the manual laptop-pull workflow.
#
# Invoked over SSH from the operator's own laptop (see the Windows
# PowerShell client) - never on a schedule. Two modes:
#
#   create              pg_dump -Fc -> validate -> checksum -> atomic
#                        promote to the final .dump name. Prints
#                        BASENAME/SHA256/SIZE_BYTES to stdout for the
#                        caller to capture. Never deletes anything.
#
#   confirm <basename>   the caller has already downloaded and verified
#                        the named backup - only now does local
#                        retention run, trimming to the newest
#                        $AQUALEDGER_LOCAL_RETENTION backups. The VPS
#                        must never delete a backup the laptop hasn't
#                        already confirmed receiving intact.
#
# Container name, DB user, and DB name are all resolved dynamically via
# `docker compose ps` / `docker exec printenv` - nothing here is
# hardcoded. No DB password is ever needed: pg_dump runs inside the
# container over its own trusted local connection.
set -euo pipefail

MODE="${1:-}"
case "$MODE" in
  create) ;;
  confirm)
    if [ "$#" -ne 2 ]; then
      echo "Usage: $0 confirm <fisherp_YYYY-MM-DD_HHMMSS.dump>" >&2
      exit 2
    fi
    CONFIRM_BASENAME="$2"
    if [[ -z "$CONFIRM_BASENAME" || "$CONFIRM_BASENAME" != fisherp_*.dump \
          || "$CONFIRM_BASENAME" == *"/"* || "$CONFIRM_BASENAME" == *"\\"* \
          || "$CONFIRM_BASENAME" == *".."* ]]; then
      echo "Usage: $0 confirm <fisherp_YYYY-MM-DD_HHMMSS.dump>" >&2
      exit 2
    fi
    ;;
  *)
    echo "Usage: $0 create" >&2
    echo "       $0 confirm <basename>" >&2
    exit 2
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.prod.yml"

BACKUP_ROOT="${AQUALEDGER_BACKUP_ROOT:-$HOME/backups}"
LOCAL_RETENTION="${AQUALEDGER_LOCAL_RETENTION:-5}"
MIN_FREE_MB="${AQUALEDGER_MIN_FREE_MB:-500}"

mkdir -p "$BACKUP_ROOT"
# Backup dumps are full production database contents - never leave them
# readable by other local accounts regardless of the invoking shell's
# umask.
chmod 700 "$BACKUP_ROOT"
LOCK_FILE="$BACKUP_ROOT/.backup.lock"
LOG_FILE="${AQUALEDGER_BACKUP_LOG:-$BACKUP_ROOT/backup.log}"
STATUS_FILE="$BACKUP_ROOT/status.json"
touch "$LOG_FILE"
chmod 600 "$LOG_FILE"

log() {
  printf '%s %s\n' "$(date -u +%FT%TZ)" "$1" >>"$LOG_FILE"
}

# --- lightweight status file for at-a-glance health checks - a single
# JSON object, overwritten each run. "phase" distinguishes a completed-
# but-not-yet-confirmed create from a fully confirmed (and therefore
# retained) backup. ---
write_status() {
  local result="$1" reason="${2:-}"
  printf '{"last_run_utc":"%s","phase":"%s","result":"%s","reason":"%s","basename":"%s","size_bytes":"%s"}\n' \
    "$(date -u +%FT%TZ)" "$MODE" "$result" "$reason" "${BASENAME:-}" "${SIZE_BYTES:-}" >"$STATUS_FILE"
  chmod 600 "$STATUS_FILE"
}

# --- locking: refuse to run if another backup (create or confirm) is
# already in progress ---
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
  log "SKIP ($MODE): another backup run is already in progress"
  exit 1
fi

fail() {
  log "FAIL ($MODE): $1"
  write_status "failure" "$1"
  exit 1
}

log "START $MODE"

if [ "$MODE" = "create" ]; then
  command -v docker >/dev/null 2>&1 || fail "docker not found on PATH"

  CONTAINER_ID="$(docker compose -f "$COMPOSE_FILE" ps -q postgres || true)"
  [ -n "$CONTAINER_ID" ] || fail "postgres container not found (is the stack up?)"

  HEALTH="$(docker inspect -f '{{.State.Health.Status}}' "$CONTAINER_ID" 2>/dev/null || echo unknown)"
  [ "$HEALTH" = "healthy" ] || fail "postgres container is not healthy (status=$HEALTH)"

  DB_USER="$(docker exec "$CONTAINER_ID" printenv POSTGRES_USER)"
  DB_NAME="$(docker exec "$CONTAINER_ID" printenv POSTGRES_DB)"
  [ -n "$DB_USER" ] && [ -n "$DB_NAME" ] || fail "could not resolve POSTGRES_USER/POSTGRES_DB from container env"

  FREE_MB="$(df -Pm "$BACKUP_ROOT" | awk 'NR==2 {print $4}')"
  [ "$FREE_MB" -ge "$MIN_FREE_MB" ] || fail "insufficient disk space (${FREE_MB}MB free, need ${MIN_FREE_MB}MB)"

  # --- backup creation: write to a .tmp path, only promote after validation ---
  TIMESTAMP="$(date -u +%Y-%m-%d_%H%M%S)"
  BASENAME="fisherp_${TIMESTAMP}.dump"
  TMP_PATH="$BACKUP_ROOT/${BASENAME}.tmp"
  FINAL_PATH="$BACKUP_ROOT/${BASENAME}"

  # Best-effort cleanup if this process is killed mid-dump (e.g. the SSH
  # session that invoked it drops) - a no-op once the file has already
  # been promoted to its final name below, since it won't exist at
  # $TMP_PATH anymore.
  trap 'rm -f "$TMP_PATH" 2>/dev/null || true' EXIT

  log "Creating dump -> ${BASENAME}.tmp"
  if ! docker exec "$CONTAINER_ID" pg_dump -U "$DB_USER" -Fc -d "$DB_NAME" >"$TMP_PATH" 2>>"$LOG_FILE"; then
    fail "pg_dump failed"
  fi

  [ -s "$TMP_PATH" ] || fail "dump file is missing or empty"

  # --- validation: the container's own pg_restore reads the archive TOC ---
  if ! docker exec -i "$CONTAINER_ID" pg_restore --list <"$TMP_PATH" >/dev/null 2>>"$LOG_FILE"; then
    fail "pg_restore --list validation failed on the new dump"
  fi

  CHECKSUM="$(sha256sum "$TMP_PATH" | awk '{print $1}')"
  SIZE_BYTES="$(stat -c%s "$TMP_PATH")"

  mv "$TMP_PATH" "$FINAL_PATH"
  echo "$CHECKSUM  $BASENAME" >"${FINAL_PATH}.sha256"
  chmod 600 "$FINAL_PATH" "${FINAL_PATH}.sha256"
  log "Backup validated: $BASENAME size=${SIZE_BYTES}B sha256=${CHECKSUM}"
  write_status "created"

  # Machine-readable summary for the caller (the Windows laptop's
  # PowerShell client) to parse. Nothing is deleted or uploaded here -
  # retention only ever happens later, via an explicit `confirm` call
  # once the caller has verified this checksum for itself.
  echo "RESULT=CREATED"
  echo "BASENAME=$BASENAME"
  echo "SHA256=$CHECKSUM"
  echo "SIZE_BYTES=$SIZE_BYTES"

  log "COMPLETE create: $BASENAME (awaiting confirm)"
  exit 0
fi

if [ "$MODE" = "confirm" ]; then
  BASENAME="$CONFIRM_BASENAME"
  FINAL_PATH="$BACKUP_ROOT/$BASENAME"

  [ -f "$FINAL_PATH" ] || fail "confirm: backup file not found: $BASENAME"
  [ -f "${FINAL_PATH}.sha256" ] || fail "confirm: checksum sidecar not found: $BASENAME"

  # --- server-side integrity check, defense-in-depth alongside the
  # laptop's own verification: independently recompute the dump's
  # SHA256 and compare it against the sidecar BEFORE any retention is
  # even considered. A mismatch fails the run and deletes nothing. ---
  EXPECTED_SHA256="$(awk '{print $1}' "${FINAL_PATH}.sha256")"
  ACTUAL_SHA256="$(sha256sum "$FINAL_PATH" | awk '{print $1}')"
  [ -n "$EXPECTED_SHA256" ] && [ "$EXPECTED_SHA256" = "$ACTUAL_SHA256" ] || \
    fail "confirm: SHA256 mismatch for $BASENAME (sidecar=${EXPECTED_SHA256:-empty} actual=$ACTUAL_SHA256) - retention skipped"
  log "Verified: $BASENAME sha256 matches sidecar ($ACTUAL_SHA256)"

  SIZE_BYTES="$(stat -c%s "$FINAL_PATH")"

  # --- retention: only ever runs here, after existence AND checksum
  # verification above both succeed - and only ever trims beyond the
  # keep-count, so a keep-count >= 1 can never delete the backup just
  # confirmed. ---
  mapfile -t LOCAL_BACKUPS < <(ls -1t "$BACKUP_ROOT"/fisherp_*.dump 2>/dev/null || true)
  if [ "${#LOCAL_BACKUPS[@]}" -gt "$LOCAL_RETENTION" ]; then
    for old in "${LOCAL_BACKUPS[@]:$LOCAL_RETENTION}"; do
      rm -f "$old" "${old}.sha256"
      log "Retention: removed local $(basename "$old")"
    done
  fi

  log "COMPLETE confirm: $BASENAME (retention applied, keep=$LOCAL_RETENTION)"
  write_status "success"

  echo "RESULT=CONFIRMED"
  echo "BASENAME=$BASENAME"
  echo "RETAINED=$LOCAL_RETENTION"
  exit 0
fi
