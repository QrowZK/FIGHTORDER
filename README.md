# FIGHTORDER
Fightorder wiki for Spring/Recoil RTS Engine And Derivs

MediaWiki instance deployed to a DreamHost shared-hosting box, managed
through this repo and GitHub Actions.

## How it works

- `config/LocalSettings.template.php` — the real `LocalSettings.php`, with
  secrets templated out as `__PLACEHOLDER__` tokens.
- `overrides/` — anything that should be rsynced on top of a fresh
  MediaWiki checkout (custom skins, extensions, images). Empty for now.
- `.github/workflows/deploy.yml` — on every push to `main`:
  1. downloads MediaWiki (version pinned by `MEDIAWIKI_VERSION` in the
     workflow),
  2. downloads the Citizen skin (pinned by `CITIZEN_VERSION`) into
     `skins/Citizen`,
  3. renders `LocalSettings.php` from the template using GitHub secrets,
  4. rsyncs the build to the DreamHost docroot over SSH (password auth),
     preserving server-side `images/` uploads and `cache/`,
  5. runs `maintenance/run.php update` to apply any schema changes.

The active skin is **Citizen** (`$wgDefaultSkin = "citizen"`), the theme
the site is built around; Vector stays loaded as a selectable fallback.
To bump the skin, change `CITIZEN_VERSION` in the workflow and push —
check the target tag's `skin.json` still declares `MediaWiki >= 1.43`.

Manually running the workflow (Actions tab → **Run workflow**) with
`run_install = true` instead runs `maintenance/run.php install` — use this
**once**, against a fresh empty database, to create the initial tables and
admin account. Every push after that should use the normal `update.php`
path (leave `run_install` as `false` / just push to `main`).

## Required GitHub secrets

Settings → Secrets and variables → Actions → **Secrets**:

| Secret | Value |
|---|---|
| `SSH_HOST` | `iad1-shared-b7-38.dreamhost.com` |
| `SSH_USER` | `fightorderadminone` |
| `SSH_PASSWORD` | (the DreamHost shell password) |
| `DEPLOY_PATH` | Absolute path to the domain's docroot, e.g. `/home/fightorderadminone/fightorder.net` |
| `WG_DB_HOST` | `mysql.fightorder.net` |
| `WG_DB_NAME` | `fightorderdb` |
| `WG_DB_USER` | `fightorderclaude` |
| `WG_DB_PASSWORD` | (the MySQL password) |
| `WG_SECRET_KEY` | 64-char hex string (generate once, never change) |
| `WG_UPGRADE_KEY` | short random hex string, only needed during install |
| `WG_ADMIN_USER` | initial wiki admin username, used only by the install step |
| `WG_ADMIN_PASSWORD` | initial wiki admin password, used only by the install step |

Settings → Secrets and variables → Actions → **Variables** (non-secret,
optional — defaults are shown in the workflow if omitted):

| Variable | Default |
|---|---|
| `WG_SITE_NAME` | `FIGHTORDER` |
| `WG_SERVER` | `https://fightorder.net` |
| `WG_EMERGENCY_CONTACT` | `admin@fightorder.net` |

## First-time setup checklist

1. Create the domain/docroot and MySQL database in the DreamHost panel
   (already done for `fightorder.net` / `fightorderdb`).
2. Add all the secrets above.
3. Confirm `DEPLOY_PATH` matches the real docroot path shown in the
   DreamHost panel for the domain.
4. Run the workflow manually with `run_install = true`.
5. Log into the wiki with the admin account and change the password if you
   want something other than the generated one.
6. From then on, just push to `main` — routine deploys run `update.php`
   automatically.

## Notes

- This uses SSH **password** auth (`sshpass`), matching what was provided
  when this was set up. Fine for a hobby project; swap to a dedicated SSH
  key if this ever needs to be more locked-down.
- MediaWiki's job queue is disabled on web requests (`$wgJobRunRate = 0`)
  since shared hosting has no background workers. Set up a DreamHost cron
  job to periodically run `php maintenance/run.php runJobs` if the wiki
  starts relying on deferred jobs (email notifications, link tables after
  bulk edits, etc).
