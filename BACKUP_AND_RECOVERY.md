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
- **Google OAuth client**: as of Sprint 19 Session 4, this setup uses a
  **dedicated personal Google Cloud OAuth client** (Desktop app type),
  created and owned by the account owner — not rclone's shared/default
  client. The retirement warning rclone used to print on every run is
  gone (verified live). See §6 for how this was migrated, where the
  client credentials live, and how to recover/rotate them.

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

## 6. Google OAuth client (migrated off the shared client — Sprint 19 Session 4)

**Done.** The `gdrive` remote (and therefore `gcrypt`, which sits on top
of it) now authenticates through a **dedicated personal Google Cloud
OAuth client**, owned by the account owner, instead of rclone's
shared/default client. rclone's retirement warning no longer appears on
any run — verified live before and after migration.

**What exists now, and where:**

- A Google Cloud project + OAuth consent screen (Testing mode, the
  account owner added as a test user) + one OAuth client ID (**Desktop
  app** type) — all created and owned by the account owner in their own
  Google Cloud Console. This project/client is **not** managed by this
  repository or this pipeline in any way.
- The client ID + client secret are stored **only** inside
  `~/.config/rclone/rclone.conf` on the VPS (`600`, owner-only) as the
  `gdrive` remote's `client_id`/`client_secret` fields. **They are not
  backed up by this pipeline, not committed, and not written anywhere
  else.** If you want a recovery copy, save them yourself (e.g. in a
  password manager) the same way you saved the crypt password in §1 —
  this document does not do that for you.
- The Drive-access token itself (what actually authorizes API calls)
  also lives only in `rclone.conf`, refreshed automatically by rclone
  as needed — no interactive login is required for normal operation,
  including through systemd (verified).

**If the token ever expires or is revoked** (e.g. you revoke access
from `myaccount.google.com/permissions`, or don't use it for an
extended period and Google expires it — routine for a Testing-mode
app): backups will start failing with an auth error in `backup.log`/
`status.json`. Re-authorize with:

```bash
rclone config reconnect gdrive:
```

This reuses the same client ID/secret already stored in `rclone.conf`
and only needs the same headless-SSH-tunnel browser flow used for the
original migration (SSH local port-forward on `53682`, open the printed
URL in your own browser, approve access). It does not touch the
`gcrypt` remote, existing backups, or retention settings.

**To rotate the client secret** (e.g. if it's ever accidentally
exposed): in Google Cloud Console → Credentials → click the OAuth
client → reset/regenerate the secret, then run
`rclone config update gdrive client_secret "<new secret>" --non-interactive`
followed by `rclone config reconnect gdrive:` to re-authorize under it.

**Recreating this from scratch** (e.g. on a replacement VPS, or if the
Google Cloud project itself is ever deleted) requires repeating the
manual Google Cloud Console steps once (project → enable Drive API →
consent screen → test user → OAuth client) — see §7 step 5 for exactly
when this applies during disaster recovery.

## 7. Disaster recovery: total VPS loss

Assumes the Oracle VPS is completely gone — destroyed, unrecoverable,
inaccessible.

**What this restores, and what it doesn't:**

| Needed for full recovery | Where it lives | This procedure restores it? |
|---|---|---|
| Database contents | Google Drive (encrypted *or* raw — either works, see step 5/7 below) | Yes — this is the point of this doc |
| Application code | GitHub | Yes — `git clone` |
| Runtime secrets (`JWT_SECRET_KEY`, `DATABASE_URL`, `POSTGRES_PASSWORD`, CORS origin, etc.) | Only in `backend/.env` and `.env` **on the old VPS** — never committed | **No** — these must be regenerated/reconfigured from scratch; a database dump does not contain them |
| Google Drive OAuth authorization (for either destination) | Your Google account + your personal OAuth client's ID/secret (Google Cloud Console, §6) | **No** — you need your saved client ID/secret (or must recreate the OAuth client in Google Cloud Console if lost) to re-authorize on the new host |
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
  the personal OAuth client ID/secret from §6, and the crypt password/
  salt if restoring from the encrypted destination) — lives only on the
  VPS (token, client ID/secret) and wherever you saved the crypt
  password yourself (§1). Must be re-authorized/re-entered on a
  replacement host; this pipeline does not back up its own credentials,
  and Google Drive authentication is entirely independent of the
  PostgreSQL data, application source, `.env` secrets, JWT secret,
  database password, and Docker configuration — restoring any one of
  these does not restore any other.
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
   `rclone config` → add the `gdrive` remote as type `drive`, supplying
   your **personal OAuth client's `client_id`/`client_secret`** (from
   wherever you saved them per §6 — Google Cloud Console → Credentials
   if you didn't save them separately; the client/project itself
   survives a VPS loss since it's not hosted on the VPS) → re-authorize
   against the same Google account (same headless-SSH-tunnel browser
   flow as initial setup). This alone is enough to restore from the
   **raw** destination.
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

## 9. Public homepage & privacy policy (Google OAuth branding)

The Google Cloud OAuth consent screen for the `gdrive`/`gcrypt` remotes (§6)
requires public application/homepage and privacy-policy URLs before it can
be moved out of Testing mode (§10). These are served by the frontend
application itself — genuinely public routes, reachable without logging
in (verified: `middleware.ts` exempts them in both directions, and both
prerender as static pages):

- **Application homepage:** `https://aqualedger.zenmediahouse.com/`
- **Privacy policy:** `https://aqualedger.zenmediahouse.com/privacy`

Neither page makes an authenticated API call or requires a session to
render, and neither discloses infrastructure details, credentials, or
internal API implementation — see `frontend/src/features/marketing/pages/`
for the source.

**Support contact:** the homepage footer and privacy policy show a single
support address, centralized in `SUPPORT_EMAIL` in
`frontend/src/lib/site-config.ts` — currently `chandansolanki618@gmail.com`.
Use that same address for the OAuth consent screen's "Support email" field
(§10 step 5) so the two stay consistent.

## 10. Google OAuth: Testing → Production checklist

This is an **operator checklist** — none of it can be done from the
codebase or by Claude Code. It only applies to the `gdrive`/`gcrypt`
backup OAuth client described in §6, not to end-user login (AquaLedger's
own authentication, §8 of the main architecture doc, does not use Google
OAuth at all).

**Why this matters:** a Google Cloud OAuth consent screen left in
*Testing* mode expires a test user's grant after roughly seven days of
inactivity (or a fixed window, depending on scope), which is the
`invalid_grant` failure this migration is meant to prevent from recurring.
Moving the consent screen to *In production* removes that expiry.

1. Deploy the public homepage and privacy policy (§9) to production.
2. Verify `https://aqualedger.zenmediahouse.com/` loads, returns 200, and
   does **not** redirect to `/login`, from a private/incognito browser
   session (no session cookie).
3. Verify `https://aqualedger.zenmediahouse.com/privacy` loads the same
   way.
4. Verify the HTTPS certificate is valid (not expired, matches the
   domain, no browser warning).
5. In Google Cloud Console → APIs & Services → OAuth consent screen, fill
   in the branding fields with:
   - **Application name:** `AquaLedger Backups`
   - **Application home page:** `https://aqualedger.zenmediahouse.com/`
   - **Application privacy policy link:** `https://aqualedger.zenmediahouse.com/privacy`
   - **Authorized domain:** `zenmediahouse.com`
   - **Support email:** `chandansolanki618@gmail.com` (§9) — keep this in
     sync with `SUPPORT_EMAIL` in `frontend/src/lib/site-config.ts` if it
     ever changes.
6. Verify `zenmediahouse.com` is a **verified domain** on the Google
   account being used (Search Console verification, or however Google
   Cloud Console prompts for it) — required before Google will accept it
   as an authorized domain.
7. Review the OAuth scopes this client actually requests (Drive access
   for `rclone`). A narrow, non-sensitive Drive scope for a single-user
   Desktop-app client used only by its own owner typically does not
   trigger Google's full verification/security-assessment process, but
   Google Cloud Console is authoritative here — follow whatever it
   prompts for before publishing.
8. Only once steps 2–7 are satisfied, change the OAuth consent screen's
   publishing status from **Testing** to **In production** in Google
   Cloud Console.
9. Do **not** run `rclone config reconnect gdrive:` unless the existing
   token has actually stopped working — publishing status alone does not
   invalidate a currently-valid token.
10. If Google does require a fresh authorization after the publishing
    status changes, reconnect using the existing documented procedure
    (§6): `rclone config reconnect gdrive:` (SSH local port-forward on
    `53682`, approve in your own browser). This does not touch `gcrypt`,
    existing backups, or retention settings.
11. Run a full manual backup: `./scripts/backup-postgres.sh` (§3).
12. Verify the new backup landed in **both** destinations:
    `rclone lsl gcrypt:weekly/` and
    `rclone lsl gdrive:AquaLedger-Backups/weekly/` (§4).
13. Verify the archive is structurally valid:
    `pg_restore --list` against the new `.dump` file (the backup script
    already does this automatically as part of §1's pipeline; re-running
    it manually here is just operator confirmation).
14. Record the result (timestamp, `status.json` contents, and the output
    of steps 12–13) somewhere durable — this is the "Day 0" baseline for
    §11 below.

## 11. Post-production 7-day OAuth validation

Moving the consent screen to Production (§10) does **not**, by itself,
prove the `invalid_grant` failure is gone — only a real validation window
does. Do not tell anyone the backup pipeline is "proven" against the
7-day expiry until this has actually been carried out and recorded; a
publishing-status change alone is not evidence.

Do not change the backup schedule (§2) for this — validate against the
existing weekly timer, not an artificially tightened one.

- **Day 0** — immediately after §10 step 14:
  - Manual backup already run; encrypted upload verified; raw upload
    verified; both remote files confirmed present; timestamp recorded.
- **Day 1:**
  - `systemctl status aqualedger-backup.timer` and
    `systemctl is-failed aqualedger-backup.service` — confirm the timer
    is still `enabled`/`active` and the last run wasn't a failure.
- **Day 6:**
  - `rclone lsl gcrypt:weekly/` (or any other read-only rclone command)
    — confirms the OAuth token is still valid for API calls *before* the
    old Testing-mode expiry window would have hit, without waiting for a
    scheduled backup.
- **Day 7 and beyond:**
  - Repeat the Day 6 `rclone` access check.
  - Let the next scheduled Sunday 02:30 UTC backup run (or trigger one
    manually if you want the checkpoint sooner — §3).
  - Verify both destinations received the new backup (§4).
  - Check `~/backups/backup.log` and `status.json` for the absence of
    `invalid_grant` or any OAuth token-refresh failure.
  - Only once this is confirmed, it is accurate to record:
    *"OAuth production-readiness validated after the previous
    testing-mode expiry window."* Record the date this was confirmed.

## 12. Files added/modified

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
  (`fisherp_20260825T181553Z.sql`) — housekeeping only, no production
  data affected. Two dangling anonymous Docker volumes from earlier
  restore drills were identified as safe to remove but the deletion
  command was blocked by Claude Code's own safety classifier; still
  pending manual cleanup (see the Session 3 report for the exact safe
  command).

**Session 4 (Google OAuth client migration — no architecture change):**
- No script or systemd changes — this session only changed
  authentication ownership, not backup logic.
- VPS-only: the `gdrive` remote's `client_id`/`client_secret` in
  `~/.config/rclone/rclone.conf` were updated to a dedicated personal
  Google Cloud OAuth client, and re-authorized (`rclone config
  reconnect gdrive:`). The `gcrypt` remote was untouched (it delegates
  to `gdrive:` and needed no changes).
- This file — rewrote §6 (migration is complete, added rotation/
  recovery instructions), updated the §7 disaster-recovery table and
  step 5 to reflect that OAuth recovery now needs the personal client's
  credentials, not just a fresh authorization against the shared one.

**Sprint 19 Session 5 (public homepage/privacy page + OAuth
production-readiness docs — no backup script or architecture change):**
- No script, systemd, or backend changes.
- `frontend/`: added the public homepage (`/`) and privacy policy
  (`/privacy`) required for the Google OAuth consent-screen branding
  review (§9), and exempted both from the authentication middleware
  without weakening protection on any existing authenticated route. See
  the frontend PR/commit for the full file list.
- This file — added §9 (public homepage/privacy URLs), §10 (Testing →
  Production checklist), §11 (post-production 7-day validation
  procedure); renumbered the old §8 "Files added/modified" to §12.

Sessions 1–4 touched no application code, Alembic migrations, or
frontend/backend business logic. Session 5 touched only the frontend's
public marketing routes and this document — no backend, database, or
backup-script changes.
