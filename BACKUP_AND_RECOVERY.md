# AquaLedger — Backup & Disaster Recovery

Companion to [DEPLOYMENT.md](DEPLOYMENT.md), which covers first-time
provisioning; this document covers protecting and recovering the
production database once the stack is already running.

**This document was rewritten as part of the Google Drive/rclone backup
retirement.** The old dual-destination Google Drive pipeline (encrypted
`gcrypt:weekly` + raw `gdrive:AquaLedger-Backups/weekly`, uploaded by a
weekly systemd timer) has been fully retired: the timer is disabled and
removed, `rclone` and its configuration have been removed from the VPS,
and the 16 backups that were stored on Google Drive have been
permanently deleted at the owner's explicit request. There is no
migration path from that data — it no longer exists anywhere. See git
history around the `Phase 4` commits for the retirement record.

The **only** supported backup mechanism going forward is a manual,
Windows-laptop-initiated pull over SSH, described below.

---

## 1. Architecture

Backups are never scheduled and never run unattended. The laptop
always initiates; the VPS never pushes anywhere.

```
Windows laptop (operator-initiated, outbound only)
        │  ssh, alias "aqualedger-backup", dedicated restricted key
        ▼
Production VPS — scripts/backup-ssh-wrapper.sh (forced command)
        │
        │  backup-postgres.sh create
        ▼
PostgreSQL container (aqualedger-postgres-1)
        │  pg_dump -Fc inside the container, own trusted local
        │  connection — no DB password ever needed
        ▼
~/backups/fisherp_<UTC timestamp>.dump.tmp
        │  pg_restore --list validates the archive TOC
        ▼
~/backups/fisherp_<UTC timestamp>.dump  (+ .sha256 sidecar)
        │  basename/sha256/size printed to stdout — NO retention yet
        ▼
        scp -O  (dump, then .sha256)
        ▼
Windows laptop: C:\AquaLedger-Backups\postgres\*.download.tmp
        │  size check, then 3-way SHA256 check (create-reported vs.
        │  downloaded sidecar vs. locally recomputed)
        ▼
   match? ──NO──▶ STOP. Files deleted. VPS backup untouched. Nothing confirmed.
        │YES
        ▼
   rename .download.tmp → final filename
        ▼
        ssh, second connection: backup-postgres.sh confirm <basename>
        ▼
VPS: independent server-side SHA256 recompute-and-compare, THEN
     retention trim to the newest 5 local .dump/.sha256 pairs
```

The VPS never deletes a backup the laptop hasn't already downloaded
and verified. The laptop never deletes anything, ever.

## 2. Required SSH Alias

The Windows client (`scripts/backup-aqualedger.ps1`) only ever
connects via the SSH config alias `aqualedger-backup` — never the
general admin alias, and never an `IdentityFile` embedded in the
script itself. The alias must already exist in
`%USERPROFILE%\.ssh\config`:

```
Host aqualedger-backup
    HostName <VPS host>
    User ubuntu
    IdentityFile C:\Users\<you>\.ssh\aqualedger-backup-ed25519
    IdentitiesOnly yes
```

The script checks this alias exists before doing anything else and
**never writes to `~/.ssh/config` itself** — if the alias is missing,
it prints this exact block and stops.

## 3. Restricted Backup SSH Key

A dedicated `ed25519` key pair, separate from the operator's general
admin key, is used only for this workflow. On the VPS, its
`authorized_keys` entry carries a forced command
(`scripts/backup-ssh-wrapper.sh`) plus
`no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding`.

The wrapper only ever executes one of three exact, anchored command
shapes — everything else is rejected before anything runs:

- `backup-postgres.sh create`
- `backup-postgres.sh confirm <basename>` (basename must match
  `fisherp_YYYY-MM-DD_HHMMSS.dump` exactly)
- `scp -f <path>` (legacy protocol) downloading exactly
  `/home/ubuntu/backups/<basename>` or `<basename>.sha256`

This key can never open an interactive shell and can never run
anything outside those three shapes, even if it were copied off the
laptop.

## 4. How To Create A Backup

From the Windows laptop, with a repository checkout present:

```powershell
.\scripts\backup-aqualedger.ps1
```

No arguments are required for normal use. The script runs the full
create → download → verify → confirm sequence in one command and
prints a stage-by-stage banner (`PostgreSQL health: PASS`, `Creating
backup: PASS`, `Backup validation: PASS`, `SHA256 generated: PASS`,
`Download: PASS`, `SHA256 verification: PASS`, then `BACKUP
SUCCESSFUL`) or a specific failure reason and the stage it failed at
(`BACKUP FAILED at stage: <stage>`).

On the VPS side, `create` mode (in `scripts/backup-postgres.sh`)
acquires an `flock` lock, checks the `postgres` container is healthy,
checks free disk space (≥500MB by default), runs `pg_dump -Fc` to a
`.tmp` file, validates it with `pg_restore --list`, computes its
SHA256, and only then atomically renames it to its final name. It
prints:

```
RESULT=CREATED
BASENAME=fisherp_2026-09-14_115027.dump
SHA256=<64-char hex>
SIZE_BYTES=<integer>
```

**`create` never deletes or retains anything.** A dropped SSH session
mid-`pg_dump` is handled by a `trap` that removes the orphaned `.tmp`
file.

## 5. How SCP Download Works

Every download uses `scp -O` (the legacy SCP protocol), because
`backup-ssh-wrapper.sh` only understands that protocol's plain
`scp -f <path>` command — not the SFTP-subsystem mode modern `scp`
negotiates by default. `backup-aqualedger.ps1` always passes `-O`.

The dump and its `.sha256` sidecar are downloaded to
`<basename>.download.tmp` / `<basename>.sha256.download.tmp` in the
local backup directory — never directly to their final names — and
are only renamed to the real filenames after every check below
passes. The script refuses to overwrite an existing local backup with
the same basename.

## 6. Local SHA256 Verification

Three independent values must all agree before anything is trusted:

- **(A)** the SHA256 `create` printed to stdout,
- **(B)** the SHA256 inside the downloaded `.sha256` sidecar file,
- **(C)** a fresh `Get-FileHash -Algorithm SHA256` computed locally
  on the just-downloaded `.dump` file.

A mismatch between any pair — plus a byte-size mismatch against the
`SIZE_BYTES` `create` reported — is a hard failure. On any failure
before this point, `confirm` is never sent, and the run's own
incomplete `.download.tmp` files are removed (never a previously
completed backup).

## 7. VPS Confirm / Retention

Only after every check in §6 passes does the laptop open a **second**
SSH connection and send `backup-postgres.sh confirm <basename>`. The
VPS independently re-verifies the SHA256 itself (recomputes and
compares against its own sidecar) before doing anything else — a
mismatch here aborts with no retention change. Only once that
succeeds does retention run, trimming `~/backups` to the newest
`AQUALEDGER_LOCAL_RETENTION` (default **5**) `.dump`/`.sha256` pairs.
It prints:

```
RESULT=CONFIRMED
BASENAME=fisherp_2026-09-14_115027.dump
RETAINED=5
```

## 8. Windows Backup Directory

Default: `C:\AquaLedger-Backups\postgres\` (override with
`-BackupRoot`). Flat layout — `fisherp_YYYY-MM-DD_HHMMSS.dump` plus
its `.sha256` sidecar, one pair per successful run.

**Every successfully verified backup is kept forever.** The script
never deletes, overwrites, or prunes anything under this directory —
disk-space management here is a manual, operator concern.

## 9. VPS Backup Directory

`/home/ubuntu/backups/` — holds exactly the newest 5 `.dump`/`.sha256`
pairs (per §7), a `backup.log`, and a `status.json` reflecting the
outcome of the most recent `create`/`confirm` run. Mode `700` on the
directory, `600` on its files.

## 10. Restore Procedure From A Windows Backup

There is no automated restore script — restore is a deliberate,
manual procedure so it can never run against the wrong target by
accident:

1. Pick the desired `.dump` from `C:\AquaLedger-Backups\postgres\`
   and verify it once more locally:
   `Get-FileHash -Algorithm SHA256` against its `.sha256` sidecar.
2. Copy it to wherever you're restoring to (a scratch VPS, a local
   Docker host — **never the live production instance**), e.g.
   `scp <file> <target>:/tmp/`.
3. Bring up a **fresh**, never-production Postgres instance:
   `docker compose -f docker-compose.prod.yml up -d postgres` against
   a brand-new, empty volume.
4. Copy the dump into the container and restore it:
   ```bash
   docker cp /tmp/<basename> <container>:/tmp/restore.dump
   docker exec <container> pg_restore -U <user> -d <db> \
     --no-owner --no-privileges -v /tmp/restore.dump
   ```
5. Verify with real checks, not just a clean exit code: row counts on
   key tables, a few known invoice/ledger totals spot-checked against
   expected values.
6. Tear down the scratch container/volume once verification is
   complete. Never point the application layer at a scratch database.

## 11. PostgreSQL Restore Procedure Notes

`pg_restore` above is invoked **without** `--clean`/`--create` — the
target database must already exist and be empty. `--no-owner
--no-privileges` avoids failing on role names that may not exist on
the restore target. This mirrors exactly how `backup-postgres.sh`
itself validates a fresh dump (`pg_restore --list`), just applied as
a real restore instead of a structural check.

## 12. Retention Behavior

| Location | Retention |
|---|---|
| VPS (`~/backups`) | Newest 5 `.dump`/`.sha256` pairs, trimmed only inside `confirm`, only after a successful checksum re-verification |
| Windows (`C:\AquaLedger-Backups\postgres\`) | Unlimited — every verified backup is kept forever, no automatic deletion |

Retention only ever trims *beyond* the keep-count — a `confirm` can
never delete the backup it was just called for.

## 13. Failure Behavior

| Failure | What happens |
|---|---|
| Postgres unhealthy / `pg_dump` fails / `pg_restore --list` fails | `create` fails before promoting the `.tmp` file; nothing new exists remotely; nothing downloaded |
| SSH failure (create or confirm) | Reported immediately; no further stage attempted |
| SCP failure / interrupted download | Local size/SHA256 check fails; `confirm` never sent; run's own temp files removed |
| SHA256 or size mismatch (any of the 3 checks) | Hard stop; `confirm` never sent; VPS backup and retention untouched |
| `confirm` SSH/exit failure | The local backup **is already saved and verified** — only the VPS's retention trim didn't run; safe to re-run `confirm` later |
| VPS-side checksum mismatch during `confirm` | VPS aborts before retention; nothing deleted |

## 14. Security Considerations

- The restricted backup key can only ever run the three fixed command
  shapes in §3 — never an arbitrary shell command.
- `backup-ssh-wrapper.sh` treats `$SSH_ORIGINAL_COMMAND` strictly as
  inert data (`[[ == ]]` / `[[ =~ ]]` comparisons only) — it is never
  `eval`'d or interpolated into an executable command line.
- No database password is ever needed anywhere in this pipeline —
  `pg_dump`/`pg_restore` run inside the container over its own
  trusted local connection.
- No `sudo` is required anywhere in the backup pipeline itself.

## 15. ⚠️ Windows Backups Are Unencrypted Full Production Data

`C:\AquaLedger-Backups\postgres\*.dump` files are **plain,
unencrypted** PostgreSQL dumps — a complete copy of the production
database, including all tenant business data, readable by anyone with
file access to that folder. This is an explicit, accepted trade-off,
not an oversight. No encryption layer is applied anywhere in this
pipeline. The only protections are whatever the laptop itself already
has: full-disk encryption, the Windows account password/lock screen,
and physical control of the device. Treat this folder accordingly.

## 16. No Google Drive / rclone Backup Support

The previous Google Drive/rclone pipeline (`gcrypt:weekly` and
`gdrive:AquaLedger-Backups/weekly`, both inside the operator's
personal Google Drive account) has been fully retired and its 16
stored backups permanently deleted. `rclone` and
`~/.config/rclone/rclone.conf` have been removed from the VPS. There
is no cloud/off-site copy of any kind in the current architecture —
see §15 and §17.

## 17. No Automatic Scheduled Backup

The `aqualedger-backup.timer`/`.service` systemd units that used to
run this weekly have been disabled, stopped, and removed from both
the VPS and this repository. There is currently **no unattended
backup mechanism of any kind** — if nobody runs
`.\scripts\backup-aqualedger.ps1`, no new backup is made. This is an
accepted consequence of the "manual only" requirement, not an
oversight — the effective RPO is "however long since the operator
last ran the script."

## 18. Manual Laptop-Initiated Backup Is The Supported Mechanism

To summarize: run `.\scripts\backup-aqualedger.ps1` from the Windows
laptop whenever a backup is wanted. That is the entire backup story
for this project today — no timer, no cloud upload, no scheduled job.
Everything above (§1–§14) describes exactly what that one command
does and how to restore from what it produces.
