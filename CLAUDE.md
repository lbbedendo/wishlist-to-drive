# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Python + Selenium scraper that collects books (title, author, URL) from Amazon wishlists, writes an HTML snapshot and a JSON file per wishlist to `output/`, then uploads those files to a Google Drive folder via a service account. Code, comments, identifiers, and log messages are in Portuguese — keep new code consistent with that.

## Commands

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp wishlist.txt.template wishlist.txt   # first time only; then edit it
python main.py        # scrape all wishlists, then upload this run's files to Drive

pip install -r requirements-dev.txt
pytest                                   # all tests (pytest.ini sets pythonpath=. and testpaths=tests)
pytest tests/test_wishlists.py::test_remove_duplicatas_pelo_id   # single test
```

There is no linter or build step. Chrome must be installed locally; ChromeDriver is fetched by `webdriver-manager` at runtime.

## Configuration

Wishlists are listed in `wishlist.txt` at the repo root — a personal, git-ignored file created from the versioned `wishlist.txt.template`. One full wishlist URL or bare ID per line; `#` starts a comment (also inline), blank lines are skipped. `wishlists.py` parses it: bare IDs become `URL_BASE_WISHLIST + ID` (amazon.com.br), invalid lines and duplicate IDs are skipped with a warning that includes `file:line`. It is kept separate from `main.py` so tests don't import Selenium.

Env vars are loaded from `.env` (see `.env.example`):

- `GDRIVE_FOLDER_ID` — target Drive folder; if unset, upload is skipped with a warning.
- `SERVICE_ACCOUNT_FILE` — optional, discouraged. If set, `gdrive.py` authenticates with that service-account JSON key; otherwise it uses Application Default Credentials (`google.auth.default`).

The project must not rely on long-lived credentials. Locally, ADC comes from `gcloud auth application-default login --impersonate-service-account=<SA>`; in GitHub Actions, from Workload Identity Federation via `google-github-actions/auth`. Either way the Drive folder must be shared with the service account's email.

## Architecture

- `main.py` — scraping pipeline. `main()` creates one headless Chrome driver, and for each URL `extrair_dados_da_wishlist()` loads the page, waits (15s) for items matching `SELETOR_LIVROS`, then `carregar_todos_os_livros()` scrolls repeatedly to trigger Amazon's infinite-scroll pagination until `#endOfListMarker` appears, the item count stops growing for `MAX_SCROLLS_SEM_PROGRESSO` scrolls, or `MAX_SCROLLS` is hit. It then saves the raw HTML and extracts each item's title/href (deduped by href) and the author from `span[id^='item-byline-']` three DOM levels up (`../../..`). On timeout it still writes HTML and an empty-`livros` JSON. `main()` returns the paths it wrote.
- Upload: the `__main__` block passes those paths to `enviar_arquivos_para_google_drive()`, so only files from the current run are uploaded (not everything in `output/`).
- `.github/workflows/wishlist-to-drive.yml` — cron-scheduled (UTC) + `workflow_dispatch` run on `ubuntu-latest` (Chrome preinstalled). Needs `id-token: write`; writes `wishlist.txt` from the `WISHLIST_TXT` secret and reads repo variables `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `GDRIVE_FOLDER_ID`. The repo is public, so run logs are public — don't log anything sensitive, and don't upload `output/` as an artifact.
- `gdrive.py` — auth (key file or ADC, see above; scope `drive.file`, so it can only see files this service account created) and `enviar_para_drive()`, which looks up a non-trashed file with the same name in the target folder and `update`s it, otherwise `create`s it. Output filenames are deterministic per wishlist ID, so reruns overwrite instead of duplicating.

JSON output shape: `{"wishlist_id": str, "titulo": str, "livros": [{"titulo", "autor", "url"}]}`.

Scraping relies on Amazon's DOM selectors above; if extraction returns nothing or looks truncated, inspect the saved `output/amazon_wishlist_<ID>.html` first.

Tests live in `tests/` and currently cover only `wishlists.py`. `main.py` imports Selenium and calls `load_dotenv()` at import time, so keep new testable logic in Selenium-free modules (as `wishlists.py` does) and use `tmp_path` for file fixtures.

`.gitignore` excludes all `*.json` and `*.html` files repo-wide (plus `service_account.json`, `.env`, `wishlist.txt`, `output/`), so any new JSON/HTML fixtures must be force-added or the ignore rules adjusted.
