# AquaLedger — Backup & Disaster Recovery

Sprint 19 Sessions 1-2. Companion to [DEPLOYMENT.md](DEPLOYMENT.md),
which covers first-time provisioning; this document covers protecting
and recovering the production database once the stack is already
running.

## 1. Architecture

Every scheduled/manual run produces **one** validated local backup, then
uploads it to **two independent Google Drive destinations**:

```
PostgreSQL container (aqualedger-postgres-1)
        │  pg_dump -Fc, run inside the container over its own
        │  trusted local connection — no DB password needed
        ▼
~/backups/fisherp_<UTC timestamp>.dump.tmp
        │  pg_restore --list validates the archive TOC
        ▼
~/backups/fisherp_<UTC timestamp>.dump   (+ .sha256 checksum file)
        │
        ├──────────────────────────────┬─────────────────────────────┐
        ▼                               ▼
rclone crypt remote "gcrypt:weekly"    rclone plain remote
        │  encrypts filenames AND      "gdrive:AquaLedger-Backups/weekly"
        │  contents before upload        │  NO encryption layer —
        ▼                                 │  meaningful filename, raw
Google Drive, opaque encrypted name        │  pg_dump bytes as-is
(the original, still-primary copy)         ▼
                                       Google Drive,
                                       fisherp_YYYY-MM-DD_HHMMSS.dump
                                       (Sprint 19 Session 2, user-requested,
                                        explicit security trade-off — §1a)
```

Both uploads must succeed and be size-verified before retention cleanup
runs on **any** of the three locations (local / encrypted remote / raw
remote) — a failure in either upload aborts the run, keeping every
existing good backup untouched everywhere.

- **Format**: `pg_dump -Fc` (PostgreSQL custom format) — chosen over
  plain SQL because it's compressed, supports `pg_restore --list` for
  structural validation without a full restore, and allows selective/
  parallel restore if ever needed. Used for both destinations.
- **Encrypted destination** (`gcrypt:weekly`, primary copy): an rclone
  `crypt` remote wraps the `gdrive` remote. Both file contents and
  file/folder *names* are encrypted (`filename_encryption standard`,
  `directory_name_encryption true`) — confirmed live: browsing the raw
  `gdrive:AquaLedger-Backups` folder shows only opaque encrypted names,
  never `fisherp_...` or `weekly`. The encryption password + salt were
  generated on the VPS, shown to the account owner once over a
  verified-by-checksum side channel, and then shredded from the VPS.
  **They are not stored anywhere else** — losing them means an existing
  encrypted backup can never be decrypted again. If you haven't stored
  them in a password manager yet, do that before anything else.
- **Raw destination** (`gdrive:AquaLedger-Backups/weekly`, added Session
  2): the plain `gdrive` remote, no crypt layer. Filenames and file
  contents are exactly the `pg_dump -Fc` output — directly downloadable
  and restorable from the Drive web UI or `rclone`, without needing the
  encryption password at all. **This is an explicit, user-requested
  security trade-off — see §1a.**
- **Off-site**: both destinations are the same Google account's Drive
  storage, not another directory or volume on the same VPS — both
  survive total VPS loss.
- **Google OAuth client**: this setup uses rclone's shared/default
  Google API client. rclone itself warns this shared client "is being
  retired and will stop working during 2026" — see §5 below for what
  that means and how to move to a personal OAuth client before it
  breaks the schedule.

### 1a. Security warning — the raw backup is unencrypted

**The raw destination (`gdrive:AquaLedger-Backups/weekly`) stores the
production database backup without any client-side encryption, at the
account owner's explicit request.** This is a deliberate, understood
trade-off, not an oversight:

- Anyone who gains access to that Google account — or to whom those
  specific files are shared — can download and restore the full
  production database, including all tenant business data.
- The encrypted `gcrypt:weekly` destination remains the primary,
  security-hardened copy; the raw copy exists purely for convenience
  (direct restorability without the encryption password).
- **Because of this, the Google account holding these backups should
  use:**
  - Multi-factor authentication (MFA) — non-negotiable given what these
    files contain.
  - A strong, unique password (not reused from any other service).
  - Periodic review of the account's connected apps/devices
    (`myaccount.google.com/permissions` and
    `myaccount.google.com/device-activity`) — remove anything
    unrecognized.
- **The raw backup file(s) must never be shared publicly** — not via a
  Drive "anyone with the link" share, not attached to an email, not
  committed to any repository.
- Repository/source-code secrets (`JWT_SECRET_KEY`, `.env` files,
  `rclone.conf`, the crypt password) remain separate from this backup
  data regardless — none of them are ever written into a database dump
  or uploaded anywhere by this pipeline.

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

**Quick health check** (single JSON object, overwritten every run —
Sprint 19 Session 3):

```bash
cat ~/backups/status.json
```

Fields: `last_run_utc`, `result` (`success`/`failure`), `reason` (empty
on success), `basename`, `size_bytes`, `encrypted_uploaded`,
`raw_uploaded`. This is the fastest way to answer "did last week's
backup actually work?" without reading the full log — but it only
reflects the *most recent* run; check the log (below) for history.

**Logs** (append-only, one line per event — never contains passwords,
tokens, or the encryption password):

```bash
tail -50 ~/backups/backup.log
```

**Latest local backup:**

```bash
ls -lt ~/backups/fisherp_*.dump | head -5
```

**Latest remote backups — encrypted destination** (through the
`gcrypt:` remote, which shows real filenames by decrypting on the fly;
browsing the underlying `gdrive:AquaLedger-Backups` folder directly
shows only opaque encrypted names for this one, which is expected and
correct):

```bash
rclone lsl gcrypt:weekly/
```

**Latest remote backups — raw destination** (plain `gdrive:` remote,
meaningful filenames, viewable directly in the Drive web UI too, under
`AquaLedger-Backups/weekly/`):

```bash
rclone lsl gdrive:AquaLedger-Backups/weekly/
```

**Scheduler status:**

```bash
systemctl status aqualedger-backup.timer
systemctl list-timers aqualedger-backup.timer
systemctl is-failed aqualedger-backup.service   # "active" or "failed", not "unknown"
journalctl -u aqualedger-backup.service --since "-14 days"
```

## 4a. Backup file permissions

`~/backups/` is `700` and every file inside it (`.dump`, `.sha256`,
`backup.log`, `status.json`) is `600` — owner (`ubuntu`) only, no
group/other read access. The script enforces this explicitly on every
run (Sprint 19 Session 3) rather than relying on the shell's umask,
since this host's default umask (`002`) would otherwise leave backups
group *and* world-readable to any other local account.

## 5. Retention policy

- **Local** (`~/backups/`): keep the newest 14 successful backups
  (~14 weeks at the weekly cadence). Configurable via
  `AQUALEDGER_LOCAL_RETENTION`.
- **Google Drive, encrypted** (`gcrypt:weekly/`): keep the newest 8
  successful weekly uploads. Configurable via
  `AQUALEDGER_REMOTE_RETENTION`.
- **Google Drive, raw** (`gdrive:AquaLedger-Backups/weekly/`): keep the
  newest 8 successful weekly uploads, independently of the encrypted
  destination's retention. Configurable via
  `AQUALEDGER_RAW_REMOTE_RETENTION`.
- Cleanup only ever runs *after* the current run's backup has been
  created, validated, **and** successfully uploaded to **both**
  destinations — never before, and never if either upload fails.
  Cleanup only ever trims backups *beyond* the keep-count on each of
  the three locations independently, so as long as each keep-count
  stays ≥ 1 it can never delete the last surviving backup from any of
  them.
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
| Database contents | Google Drive (encrypted *or* raw — either works, see step 5/7 below) | Yes — this is the point of this doc |
| Application code | GitHub | Yes — `git clone` |
| Runtime secrets (`JWT_SECRET_KEY`, `DATABASE_URL`, `POSTGRES_PASSWORD`, CORS origin, etc.) | Only in `backend/.env` and `.env` **on the old VPS** — never committed | **No** — these must be regenerated/reconfigured from scratch; a database dump does not contain them |
| Google Drive OAuth authorization (for either destination) | Your Google account | **No** — re-authorize on the new host, same as initial setup |
| Crypt encryption password/salt (only needed if restoring from the *encrypted* destination) | Wherever you stored the password after §1 above | **No** — you must have your own saved copy, or the encrypted destination's dumps are permanently unreadable. **The raw destination does not need this at all**, which is precisely why it exists. |

Do not assume a database backup alone is a full disaster-recovery
package — it explicitly is not. Full recovery requires five genuinely
separate artifacts, only one of which this backup pipeline provides:

- **A. Database backup** — from Google Drive (encrypted or raw). This
  is what this document's pipeline protects.
- **B. Application source code** — from GitHub (`git clone`), not from
  any backup.
- **C. Application secrets/config** (`JWT_SECRET_KEY`, `.env`,
  `backend/.env`, `POSTGRES_PASSWORD`, CORS origins) — lives only on
  the VPS, never committed, never backed up by this pipeline. Must be
  regenerated from scratch on a replacement host.
- **D. Google Drive/rclone authentication** (the `rclone.conf` token,
  and the crypt password/salt if restoring from the encrypted
  destination) — lives only on the VPS (token) and wherever you saved
  the crypt password yourself (§1). Must be re-authorized/re-entered on
  a replacement host; this pipeline does not back up its own
  credentials.
- **E. VPS rebuild + Docker/application redeployment** — provisioning,
  Docker Engine + rclone install, `docker compose up`, nginx/TLS — see
  DEPLOYMENT.md.

The table below maps each artifact to where it actually lives; the
numbered sequence after it is the order of operations that ties A–E
together into a working system again.

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
   initial setup). This alone is enough to restore from the **raw**
   destination.
   - **If restoring from the encrypted destination instead** (the
     primary copy), also add the `gcrypt` crypt remote pointing at
     `gdrive:AquaLedger-Backups`, entering **the same encryption
     password and salt you saved** in §1. Verify with
     `rclone lsl gcrypt:weekly/` — you should see the real backup
     filenames.
   - **If restoring from the raw destination**, no crypt password is
     needed at all — verify with
     `rclone lsl gdrive:AquaLedger-Backups/weekly/`.
6. **Bring up Postgres only** (not the full stack yet):
   ```bash
   docker compose -f docker-compose.prod.yml up -d postgres
   ```
   Wait for it to report healthy (`docker compose ps`).
7. **Download and restore the latest backup** — from whichever
   destination you set up in step 5:
   ```bash
   # From the raw destination (no crypt password required):
   SOURCE=gdrive:AquaLedger-Backups/weekly
   # — or, from the encrypted destination instead:
   # SOURCE=gcrypt:weekly

   LATEST=$(rclone lsf "$SOURCE/" | sort | tail -1)
   rclone copy "$SOURCE/$LATEST" /tmp/
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

## 8. Files added/modified

**Session 1:**
- `scripts/backup-postgres.sh` — the backup pipeline itself.
- `scripts/systemd/aqualedger-backup.service` /
  `aqualedger-backup.timer` — the schedule (copied to
  `/etc/systemd/system/` on the VPS; not auto-installed by git alone,
  see §2).
- This file.

**Session 2:**
- `scripts/backup-postgres.sh` — added the second, raw upload
  destination and its independent retention; deferred all retention
  until both uploads succeed. No systemd unit changes were needed (the
  timer just re-runs the same script path).
- This file — documented the dual-destination architecture and the
  unencrypted-storage security trade-off (§1a).

**Session 3 (operational hardening — no architecture change):**
- `scripts/backup-postgres.sh` — explicit `chmod 700`/`600` on the
  backup directory and every file it creates (dumps, checksums, log,
  new status file), independent of the shell's umask; added
  `status.json` for at-a-glance health checks (§4).
- `scripts/systemd/aqualedger-backup.service` — added `TimeoutStartSec=
  1800` (previously unbounded — a hung upload could have blocked the
  lock forever) and `NoNewPrivileges=true`.
- This file — added §4a (backup file permissions), restructured §7 with
  an explicit A–E artifact breakdown for disaster recovery.
- Removed a pre-Session-1 leftover test file
  (`fisherp_20260825T181553Z.sql`) and two dangling anonymous Docker
  volumes left over from earlier restore drills — housekeeping only,
  no production data affected.

Nothing in any session touched application code, Alembic migrations,
or the frontend/backend business logic.
