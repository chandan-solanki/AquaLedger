#!/usr/bin/env bash
# Production PostgreSQL backup: pg_dump (custom format, run inside the
# postgres container) -> validate -> upload to TWO independent Google
# Drive destinations -> prune retention on each independently:
#   1. the encrypted rclone "gcrypt" remote (client-side encrypted
#      filenames + contents) - the original, still-primary copy.
#   2. a plain "gdrive" remote with meaningful filenames - an
#      explicit, user-requested, less-secure raw copy (Sprint 19
#      Session 2). See BACKUP_AND_RECOVERY.md for the security
#      trade-off this implies.
# Retention only ever runs after BOTH uploads succeed - a failure in
# either one aborts the run before any cleanup.
#
# Container name, DB user, and DB name are all resolved dynamically via
# `docker compose ps` / `docker exec printenv` - nothing here is hardcoded
# to today's specific container names or credentials. No DB password is
# ever needed: pg_dump runs inside the container over its own trusted
# local connection.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.prod.yml"

BACKUP_ROOT="${AQUALEDGER_BACKUP_ROOT:-$HOME/backups}"
RCLONE_REMOTE="${AQUALEDGER_RCLONE_REMOTE:-gcrypt:weekly}"
REMOTE_RETENTION="${AQUALEDGER_REMOTE_RETENTION:-8}"
RAW_RCLONE_REMOTE="${AQUALEDGER_RAW_RCLONE_REMOTE:-gdrive:AquaLedger-Backups/weekly}"
RAW_REMOTE_RETENTION="${AQUALEDGER_RAW_REMOTE_RETENTION:-8}"
LOCAL_RETENTION="${AQUALEDGER_LOCAL_RETENTION:-14}"
MIN_FREE_MB="${AQUALEDGER_MIN_FREE_MB:-500}"

mkdir -p "$BACKUP_ROOT"
# Backup dumps are full production database contents - never leave them
# readable by other local accounts regardless of the invoking shell's
# umask (this host's default umask is 002, which would otherwise leave
# both the directory and every file group/world-readable).
chmod 700 "$BACKUP_ROOT"
LOCK_FILE="$BACKUP_ROOT/.backup.lock"
LOG_FILE="${AQUALEDGER_BACKUP_LOG:-$BACKUP_ROOT/backup.log}"
STATUS_FILE="$BACKUP_ROOT/status.json"
touch "$LOG_FILE"
chmod 600 "$LOG_FILE"

log() {
  printf '%s %s\n' "$(date -u +%FT%TZ)" "$1" >>"$LOG_FILE"
}

# --- lightweight status file for at-a-glance health checks (Sprint 19
# Session 3) - a single JSON object, overwritten each run. Not a
# substitute for the log, just a fast "did the last run succeed" check
# that doesn't require parsing log lines. ---
write_status() {
  local result="$1" reason="${2:-}"
  printf '{"last_run_utc":"%s","result":"%s","reason":"%s","basename":"%s","size_bytes":"%s","encrypted_uploaded":%s,"raw_uploaded":%s}\n' \
    "$(date -u +%FT%TZ)" "$result" "$reason" "${BASENAME:-}" "${SIZE_BYTES:-}" \
    "${ENCRYPTED_UPLOADED:-false}" "${RAW_UPLOADED:-false}" >"$STATUS_FILE"
  chmod 600 "$STATUS_FILE"
}

# --- locking: refuse to run if another backup is already in progress ---
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
  log "SKIP: another backup run is already in progress"
  exit 1
fi

log "START backup run"

ENCRYPTED_UPLOADED=false
RAW_UPLOADED=false

fail() {
  log "FAIL: $1"
  write_status "failure" "$1"
  exit 1
}

# --- preflight ---
command -v docker >/dev/null 2>&1 || fail "docker not found on PATH"
command -v rclone >/dev/null 2>&1 || fail "rclone not found on PATH"

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

log "Creating dump -> ${BASENAME}.tmp"
if ! docker exec "$CONTAINER_ID" pg_dump -U "$DB_USER" -Fc -d "$DB_NAME" >"$TMP_PATH" 2>>"$LOG_FILE"; then
  rm -f "$TMP_PATH"
  fail "pg_dump failed"
fi

[ -s "$TMP_PATH" ] || { rm -f "$TMP_PATH"; fail "dump file is missing or empty"; }

# --- validation: the container's own pg_restore reads the archive TOC ---
if ! docker exec -i "$CONTAINER_ID" pg_restore --list <"$TMP_PATH" >/dev/null 2>>"$LOG_FILE"; then
  rm -f "$TMP_PATH"
  fail "pg_restore --list validation failed on the new dump"
fi

CHECKSUM="$(sha256sum "$TMP_PATH" | awk '{print $1}')"
SIZE_BYTES="$(stat -c%s "$TMP_PATH")"

mv "$TMP_PATH" "$FINAL_PATH"
echo "$CHECKSUM  $BASENAME" >"${FINAL_PATH}.sha256"
chmod 600 "$FINAL_PATH" "${FINAL_PATH}.sha256"
log "Backup validated: $BASENAME size=${SIZE_BYTES}B sha256=${CHECKSUM}"

verify_remote_upload() {
  local label="$1" remote="$2"
  local remote_size
  remote_size="$(rclone size "${remote}/${BASENAME}" --json 2>>"$LOG_FILE" | grep -o '"bytes":[0-9]*' | head -1 | cut -d: -f2 || true)"
  if [ "$remote_size" != "$SIZE_BYTES" ]; then
    fail "$label remote size mismatch after upload (local=${SIZE_BYTES}B remote=${remote_size:-missing}) - local backup retained"
  fi
  log "$label upload verified: remote size matches local (${SIZE_BYTES}B) at ${remote}/${BASENAME}"
}

# --- upload 1: encrypted destination (existing, primary copy) - only a
# validated, completed backup is ever uploaded ---
log "Uploading (encrypted) to $RCLONE_REMOTE"
if ! rclone copy "$FINAL_PATH" "${RCLONE_REMOTE}/" --checksum >>"$LOG_FILE" 2>&1; then
  fail "encrypted upload failed (validated local backup retained at $FINAL_PATH)"
fi
verify_remote_upload "Encrypted" "$RCLONE_REMOTE"
ENCRYPTED_UPLOADED=true

# --- upload 2: raw/direct destination (Sprint 19 Session 2, user-
# requested) - plain gdrive remote, no crypt layer, meaningful filename ---
log "Uploading (raw, unencrypted) to $RAW_RCLONE_REMOTE"
if ! rclone copy "$FINAL_PATH" "${RAW_RCLONE_REMOTE}/" --checksum >>"$LOG_FILE" 2>&1; then
  fail "raw upload failed (validated local backup and encrypted remote copy retained)"
fi
verify_remote_upload "Raw" "$RAW_RCLONE_REMOTE"
RAW_UPLOADED=true

# --- retention: only runs after BOTH uploads above are fully verified,
# and only ever trims beyond each keep-count, so it can never remove the
# last surviving backup from any of the three locations. ---
mapfile -t LOCAL_BACKUPS < <(ls -1t "$BACKUP_ROOT"/fisherp_*.dump 2>/dev/null || true)
if [ "${#LOCAL_BACKUPS[@]}" -gt "$LOCAL_RETENTION" ]; then
  for old in "${LOCAL_BACKUPS[@]:$LOCAL_RETENTION}"; do
    rm -f "$old" "${old}.sha256"
    log "Retention: removed local $(basename "$old")"
  done
fi

mapfile -t REMOTE_BACKUPS < <(rclone lsf "${RCLONE_REMOTE}/" 2>>"$LOG_FILE" | grep '^fisherp_.*\.dump$' | sort -r || true)
if [ "${#REMOTE_BACKUPS[@]}" -gt "$REMOTE_RETENTION" ]; then
  for old in "${REMOTE_BACKUPS[@]:$REMOTE_RETENTION}"; do
    rclone deletefile "${RCLONE_REMOTE}/${old}" && log "Retention: removed encrypted remote $old"
  done
fi

mapfile -t RAW_REMOTE_BACKUPS < <(rclone lsf "${RAW_RCLONE_REMOTE}/" 2>>"$LOG_FILE" | grep '^fisherp_.*\.dump$' | sort -r || true)
if [ "${#RAW_REMOTE_BACKUPS[@]}" -gt "$RAW_REMOTE_RETENTION" ]; then
  for old in "${RAW_REMOTE_BACKUPS[@]:$RAW_REMOTE_RETENTION}"; do
    rclone deletefile "${RAW_RCLONE_REMOTE}/${old}" && log "Retention: removed raw remote $old"
  done
fi

log "COMPLETE backup run: $BASENAME OK"
write_status "success"
exit 0
