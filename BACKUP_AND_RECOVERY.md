# AquaLedger — Backup & Disaster Recovery

Sprint 19 Session 1. Companion to [DEPLOYMENT.md](DEPLOYMENT.md), which
covers first-time provisioning; this document covers protecting and
recovering the production database once the stack is already running.

## 1. Architecture

```
PostgreSQL container (aqualedger-postgres-1)
        │  pg_dump -Fc, run inside the container over its own
        │  trusted local connection — no DB password needed
        ▼
~/backups/fisherp_<UTC timestamp>.dump.tmp
        │  pg_restore --list validates the archive TOC
        ▼
~/backups/fisherp_<UTC timestamp>.dump   (+ .sha256 checksum file)
        │  rclone copy, through the "gcrypt" remote
        ▼
rclone crypt remote "gcrypt:weekly"
        │  client-side encrypts both file contents AND filenames
        │  before anything leaves the VPS
        ▼
rclone remote "gdrive:AquaLedger-Backups/weekly/<opaque-encrypted-name>"
        │
        ▼
Google Drive (personal account) — genuinely off-site
```

- **Format**: `pg_dump -Fc` (PostgreSQL custom format) — chosen over
  plain SQL because it's compressed, supports `pg_restore --list` for
  structural validation without a full restore, and allows selective/
  parallel restore if ever needed.
- **Encryption**: an rclone `crypt` remote (`gcrypt`) wraps the `gdrive`
  remote. Both file contents and file/folder *names* are encrypted
  (`filename_encryption standard`, `directory_name_encryption true`) —
  confirmed live: browsing the raw `gdrive:AquaLedger-Backups` folder
  shows only opaque encrypted names, never `fisherp_...` or `weekly`.
  The encryption password + salt were generated on the VPS, shown to
  the account owner once over a verified-by-checksum side channel, and
  then shredded from the VPS. **They are not stored anywhere else** —
  losing them means an existing encrypted backup can never be decrypted
  again. If you haven't stored them in a password manager yet, do that
  before anything else.
- **Off-site**: this is a separate Google account's Drive storage, not
  another directory or volume on the same VPS — it survives total VPS
  loss.
- **Google OAuth client**: this setup uses rclone's shared/default
  Google API client. rclone itself warns this shared client "is being
  retired and will stop working during 2026" — see §5 below for what
  that means and how to move to a personal OAuth client before it
  breaks the schedule.

## 2. Schedule

- systemd timer `aqualedger-backup.timer`, installed from
  `scripts/systemd/aqualedger-backup.timer` into
  `/etc/systemd/system/`, `enable --now`'d.
- Fires every **Sunday 02:30 UTC** (`OnCalendar=Sun *-*-* 02:30:00`),
  ±5 minutes of jitter (`RandomizedDelaySec`).
- `Persistent=true`: if the VPS is down at the scheduled time, the
  backup runs as soon as it comes back up instead of silently skipping
  that week.
- **Verified to survive a real reboot** (`sudo reboot`, not just
  `systemctl restart`) — the timer came back `enabled`/`active` with a
  correct next-trigger time, with no manual re-enable step.

## 3. Manual backup

To trigger a backup immediately, on the VPS:

```bash
cd ~/AquaLedger
./scripts/backup-postgres.sh
echo "exit code: $?"
```

Exit code `0` = success. Any non-zero exit means something in the
pipeline failed — check the log (§4) for the reason. A failed run never
deletes an existing good local or remote backup, and never leaves a
half-written file at the final `.dump` name (failures only ever leave
a `.dump.tmp`, which is not treated as a valid backup by anything).

Concurrent runs are safe: a second invocation while one is already
running exits immediately with `SKIP: another backup run is already in
progress` (via `flock` on `~/backups/.backup.lock`) rather than racing
it.

## 4. Checking backup status

**Logs** (append-only, one line per event — never contains passwords,
tokens, or the encryption password):

```bash
tail -50 ~/backups/backup.log
```

**Latest local backup:**

```bash
ls -lt ~/backups/fisherp_*.dump | head -5
```

**Latest remote backups** (through the encrypted remote, so this shows
real filenames — the raw `gdrive:` side only ever shows opaque
encrypted names, which is expected and correct):

```bash
rclone lsl gcrypt:weekly/
```

**Scheduler status:**

```bash
systemctl status aqualedger-backup.timer
systemctl list-timers aqualedger-backup.timer
journalctl -u aqualedger-backup.service --since "-14 days"
```

## 5. Retention policy

- **Local** (`~/backups/`): keep the newest 14 successful backups
  (~14 weeks at the weekly cadence). Configurable via
  `AQUALEDGER_LOCAL_RETENTION`.
- **Google Drive** (`gcrypt:weekly/`): keep the newest 8 successful
  weekly uploads. Configurable via `AQUALEDGER_REMOTE_RETENTION`.
- Cleanup only ever runs *after* the current run's backup has been
  created, validated, **and** successfully uploaded — never before.
  Cleanup only ever trims backups *beyond* the keep-count, so as long
  as the keep-count stays ≥ 1 it can never delete the last surviving
  backup, local or remote.
- At time of writing the database is ~10 MB and the VPS has ~32 GB
  free — retention counts are generous relative to actual usage, not a
  disk-pressure necessity. Revisit only if real data volume grows
  enough to matter.

## 6. Moving off the shared Google OAuth client (before it's retired)

rclone's own client warned during setup that its shared Google Drive
API client "is being retired and will stop working during 2026." This
setup currently relies on it. Before it's retired, create a personal
OAuth client so backups don't silently start failing:

1. In the [Google Cloud Console](https://console.cloud.google.com/),
   create a project (or reuse one), enable the **Google Drive API**,
   and configure an OAuth consent screen (Testing mode is fine for a
   single personal account).
2. Create an **OAuth client ID** of type **Desktop app**. Download/copy
   the Client ID and Client Secret — treat the secret exactly like a
   password (never commit it, never paste it anywhere but rclone's own
   config prompt).
3. On the VPS: `rclone config` → edit the `gdrive` remote → supply the
   new `client_id`/`client_secret` → re-authorize (same headless-SSH-
   tunnel browser flow used for initial setup — see the Sprint 19
   Session 1 chat log for the exact steps if needed).
4. Verify with `rclone lsd gdrive:` before considering it done.

This is a known, real deadline — not a hypothetical — but wasn't
completed in this session because it requires interactive steps in the
Google Cloud Console (project/consent-screen/client creation) that only
the account owner can perform via a browser.

## 7. Disaster recovery: total VPS loss

Assumes the Oracle VPS is completely gone — destroyed, unrecoverable,
inaccessible.

**What this restores, and what it doesn't:**

| Needed for full recovery | Where it lives | This procedure restores it? |
|---|---|---|
| Database contents | Google Drive (encrypted) | Yes — this is the point of this doc |
| Application code | GitHub | Yes — `git clone` |
| Runtime secrets (`JWT_SECRET_KEY`, `DATABASE_URL`, `POSTGRES_PASSWORD`, CORS origin, etc.) | Only in `backend/.env` and `.env` **on the old VPS** — never committed | **No** — these must be regenerated/reconfigured from scratch; a database dump does not contain them |
| Google Drive OAuth authorization + crypt encryption password/salt | Your Google account + wherever you stored the password after §1 above | **No** — you must have your own saved copy of the encryption password, or the restored dump is permanently unreadable |

Do not assume a database backup alone is a full disaster-recovery
package — it explicitly is not.

**Recovery sequence:**

1. **Provision a replacement VPS.** Same or greater spec than the
   original (1 vCPU / ~6 GB RAM was the tested baseline).
2. **Install Docker CE** via the official Docker apt repository (see
   DEPLOYMENT.md §2 for the exact package list), and **install rclone**
   via `curl https://rclone.org/install.sh | sudo bash`.
3. **Clone the application repository:**
   ```bash
   git clone <this repo's URL> ~/AquaLedger
   cd ~/AquaLedger
   ```
4. **Recreate production secrets/configuration** — `backend/.env` and
   the root `.env`, following `backend/.env.production.example` and
   `.env.production.example` as templates (see DEPLOYMENT.md §4). These
   are new secrets, not recovered from anywhere — generate a fresh
   `JWT_SECRET_KEY`, a fresh `POSTGRES_PASSWORD`, etc. (Old tokens/
   sessions issued by the destroyed VPS are naturally invalidated by
   this, which is correct.)
5. **Recreate the rclone configuration** on the new host:
   `rclone config` → add the `gdrive` remote (re-authorize against the
   same Google account — same headless-SSH-tunnel browser flow as
   initial setup) → add the `gcrypt` crypt remote pointing at
   `gdrive:AquaLedger-Backups`, entering **the same encryption password
   and salt you saved** in §1. Verify with `rclone lsl gcrypt:weekly/`
   — you should see the real backup filenames.
6. **Bring up Postgres only** (not the full stack yet):
   ```bash
   docker compose -f docker-compose.prod.yml up -d postgres
   ```
   Wait for it to report healthy (`docker compose ps`).
7. **Download and restore the latest backup:**
   ```bash
   LATEST=$(rclone lsf gcrypt:weekly/ | sort | tail -1)
   rclone copy "gcrypt:weekly/$LATEST" /tmp/
   docker cp "/tmp/$LATEST" aqualedger-postgres-1:/tmp/restore.dump
   docker exec aqualedger-postgres-1 pg_restore -U <POSTGRES_USER> \
     -d <POSTGRES_DB> --no-owner --no-privileges -v /tmp/restore.dump
   ```
   (`<POSTGRES_USER>`/`<POSTGRES_DB>` from the `.env` you just created
   in step 4 — the database must already exist and be empty, which it
   will be right after step 6's fresh container start.)
8. **Start the rest of the stack:**
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```
9. **Reconfigure the host layer**: nginx reverse proxy config, TLS
   certificate (Let's Encrypt if a domain is available, or the
   self-signed-on-bare-IP approach otherwise — see DEPLOYMENT.md §11
   and the Sprint 18 Session 5 chat log), iptables rules for ports
   80/443 (`sudo netfilter-persistent save` after adding them — this
   VPS image's default firewall rejects everything but SSH until
   explicitly opened).
10. **Run smoke tests**: login, session check, dashboard, one document/
    PDF fetch (e.g. an existing invoice), and confirm platform-admin
    access still works for the known admin account restored from the
    dump.

## 8. Files added this session

- `scripts/backup-postgres.sh` — the backup pipeline itself.
- `scripts/systemd/aqualedger-backup.service` /
  `aqualedger-backup.timer` — the schedule (copied to
  `/etc/systemd/system/` on the VPS; not auto-installed by git alone,
  see §2).
- This file.

Nothing in this session touched application code, Alembic migrations,
or the frontend/backend business logic.
