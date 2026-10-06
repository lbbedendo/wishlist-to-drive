# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Python + Selenium scraper that collects books (title, author, URL) from Amazon wishlists, writes an HTML snapshot and a JSON file per wishlist to `output/`, then uploads those files to a Google Drive folder via OAuth as the user. Code, comments, identifiers, and log messages are in Portuguese — keep new code consistent with that.

## Commands

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp wishlist.txt.template wishlist.txt   # first time only; then edit it
python autorizar_google_drive.py        # first time only (or when the token is revoked): OAuth consent + Drive folder
python main.py        # scrape all wishlists, then upload this run's files to Drive

pip install -r requirements-dev.txt
pytest                                   # all tests (pytest.ini sets pythonpath=. and testpaths=tests)
pytest tests/test_wishlists.py::test_remove_duplicatas_pelo_id   # single test
```

There is no linter or build step. Chrome must be installed locally; ChromeDriver is fetched by `webdriver-manager` at runtime.

## Configuration

Wishlists are listed in `wishlist.txt` at the repo root — a personal, git-ignored file created from the versioned `wishlist.txt.template`. One full wishlist URL or bare ID per line; `#` starts a comment (also inline), blank lines are skipped. `wishlists.py` parses it: bare IDs become `URL_BASE_WISHLIST + ID` (amazon.com.br), invalid lines and duplicate IDs are skipped with a warning that includes `file:line`. It is kept separate from `main.py` so tests don't import Selenium.

Env vars are loaded from `.env` (see `.env.example`):

- `GDRIVE_FOLDER_ID` — target Drive folder; if unset, upload is skipped with a warning. It must be a folder **created by this app** (see below).
- `GOOGLE_DRIVE_TOKEN_FILE` — optional path to the OAuth token file (default `google_drive_token.json`).

Drive auth is OAuth 2.0 as the user (installed-app flow), not a service account: service accounts have no Drive storage quota and get `403 storageQuotaExceeded` uploading to a personal "My Drive". `python autorizar_google_drive.py` runs once: it reads the Desktop OAuth client from `client_secret.json`, opens the browser for consent, writes an `authorized_user` JSON with the refresh token (mode 600), and gets-or-creates a `wishlist-to-drive` folder, printing its ID. The scope is `drive.file`, so the app can only see files/folders it created — a hand-made folder fails with `appNotAuthorizedToFile`, and access is tied to that OAuth client ID (a new client can't see old files). The refresh token is a long-lived credential (accepted trade-off); the consent screen must be "In production" or tokens expire in 7 days. `client_secret.json` and `google_drive_token.json` are git-ignored.

## Architecture

- `main.py` — scraping pipeline. `main()` creates one headless Chrome driver, and for each URL `extrair_dados_da_wishlist()` loads the page, waits (15s) for items matching `SELETOR_LIVROS`, then `carregar_todos_os_livros()` scrolls repeatedly to trigger Amazon's infinite-scroll pagination until `#endOfListMarker` appears, the item count stops growing for `MAX_SCROLLS_SEM_PROGRESSO` scrolls, or `MAX_SCROLLS` is hit. It then saves the raw HTML and extracts each item's title/href (deduped by href) and the author from `span[id^='item-byline-']` three DOM levels up (`../../..`). On timeout it still writes HTML and an empty-`livros` JSON. `main()` returns the paths it wrote.
- Upload and exit code: `main()` returns `(arquivos_para_upload, sucesso)`. A wishlist with zero books (timeout, CAPTCHA, private list) is a failure: its HTML/JSON are still written locally for debugging but are **not** uploaded, so a bad run never overwrites good files in Drive. The `__main__` block uploads only the current run's successful files and exits 1 if any wishlist failed, any upload failed, or `wishlist.txt` is missing/empty — this is what turns a scheduled GitHub Actions run red. A missing `GDRIVE_FOLDER_ID` only skips the upload locally; the workflow checks for it explicitly.
- `.github/workflows/wishlist-to-drive.yml` — cron-scheduled (UTC) + `workflow_dispatch` run on `ubuntu-latest` (Chrome preinstalled). Writes `wishlist.txt` from the `WISHLIST_TXT` secret and the token file from the `GOOGLE_DRIVE_TOKEN` secret into `$RUNNER_TEMP` (passed via `GOOGLE_DRIVE_TOKEN_FILE`); reads repo variable `GDRIVE_FOLDER_ID`. The repo is public, so run logs are public — don't log anything sensitive, and don't upload `output/` as an artifact.
- `gdrive.py` — `carregar_credenciais()` loads the token file and refreshes it immediately, so a missing/revoked token fails fast with a clear message; and `enviar_para_drive()`, which looks up a non-trashed file with the same name in the target folder and `update`s it, otherwise `create`s it. Output filenames are deterministic per wishlist ID, so reruns overwrite instead of duplicating.

JSON output shape: `{"wishlist_id": str, "titulo": str, "livros": [{"titulo", "autor", "url"}]}`.

Scraping relies on Amazon's DOM selectors above; if extraction returns nothing or looks truncated, inspect the saved `output/amazon_wishlist_<ID>.html` first.

Tests live in `tests/` and currently cover only `wishlists.py`. `main.py` imports Selenium and calls `load_dotenv()` at import time, so keep new testable logic in Selenium-free modules (as `wishlists.py` does) and use `tmp_path` for file fixtures.

`.gitignore` excludes all `*.json` and `*.html` files repo-wide (plus `client_secret.json`, `google_drive_token.json`, `.env`, `wishlist.txt`, `output/`), so any new JSON/HTML fixtures must be force-added or the ignore rules adjusted.
