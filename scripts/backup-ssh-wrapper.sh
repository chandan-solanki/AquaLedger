#!/usr/bin/env bash
# Forced-command wrapper for the dedicated AquaLedger backup SSH key.
#
# Installed as the `command=` value on ONE specific authorized_keys
# entry (see BACKUP_AND_RECOVERY.md) - never invoked directly, never
# reachable as a normal shell. sshd sets $SSH_ORIGINAL_COMMAND to
# whatever the client actually asked for; every branch below is an
# exact, fully-anchored match against that string. Anything that
# doesn't match one of the three allowed shapes is rejected outright,
# unexecuted - there is no blacklist/escaping logic to get wrong here,
# because nothing not explicitly allowed is ever passed to exec.
#
# $SSH_ORIGINAL_COMMAND is only ever treated as inert string DATA
# (compared with [[ == ]] / [[ =~ ]]) - it is never eval'd, never
# interpolated into a command line unquoted, and never itself executed.
# A payload like "$(id)" or "; rm -rf /" embedded in it is therefore
# never expanded or run - it just fails every pattern below as ordinary
# text and falls through to the reject branch.
set -euo pipefail

# Fixed, hardcoded destinations - never supplied by the client. The
# client's only influence on any of this is the validated basename
# captured out of its own command string.
REAL_SCRIPT="/home/ubuntu/AquaLedger/scripts/backup-postgres.sh"
BACKUP_DIR="/home/ubuntu/backups"
SCP_BIN="/usr/bin/scp"

# The legacy scp client sends the bare, unqualified command name "scp"
# in SSH_ORIGINAL_COMMAND (confirmed empirically: `scp -O` against this
# VPS sends exactly `scp -f <path>`, never an absolute path) - that is
# what must be MATCHED. What gets EXECUTED is always the hardcoded
# absolute $SCP_BIN above, never anything PATH-resolved or client-supplied.
SCP_CMD_NAME="scp"

BASENAME_RE='fisherp_[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{6}\.dump'

reject() {
  echo "Rejected: $1" >&2
  exit 2
}

CMD="${SSH_ORIGINAL_COMMAND:-}"
[ -n "$CMD" ] || reject "no command supplied - interactive shell/PTY access is not permitted through this key"

if [[ "$CMD" == "backup-postgres.sh create" ]]; then
  exec "$REAL_SCRIPT" create

elif [[ "$CMD" =~ ^backup-postgres\.sh\ confirm\ (${BASENAME_RE})$ ]]; then
  exec "$REAL_SCRIPT" confirm "${BASH_REMATCH[1]}"

elif [[ "$CMD" =~ ^${SCP_CMD_NAME}\ -f\ ${BACKUP_DIR}/(${BASENAME_RE}(\.sha256)?)$ ]]; then
  # Legacy-protocol scp download only ("-f" = server is the source).
  # Requires the Windows client to use `scp -O` (see BACKUP_AND_RECOVERY.md);
  # modern default scp negotiates the sftp subsystem instead, which this
  # wrapper does not and cannot speak, and therefore correctly never
  # matches any branch here.
  exec "$SCP_BIN" -f "${BACKUP_DIR}/${BASH_REMATCH[1]}"

else
  reject "only 'backup-postgres.sh create', 'backup-postgres.sh confirm <basename>', or 'scp -O' downloading an existing backup/checksum file are permitted"
fi
