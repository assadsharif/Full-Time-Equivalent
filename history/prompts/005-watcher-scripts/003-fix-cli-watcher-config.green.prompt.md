---
id: 003
title: Fix CLI watcher config.get() on Pydantic model
stage: green
date: 2026-02-04
surface: agent
model: claude-sonnet-4-5-20250929
feature: 005-watcher-scripts
branch: master
user: asad
command: please continue working
labels: ["bugfix","pydantic","config","cli-watcher","e2e"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - src/cli/watcher.py
tests:
 - tests/cli/test_watcher.py (28 passed)
 - tests/cli/test_e2e.py (11 passed)
 - tests/cli/* (291 passed)
 - Full suite: 927 passed, 10 skipped
---

## Prompt

please continue working

## Response snapshot

Fixed 3 CLI test failures in `test_watcher_start_success`, `test_watcher_lifecycle_happy_path`, and `test_full_daily_workflow`. All failures shared a single root cause: `src/cli/watcher.py` called `config.get("key", default)` (dict API) on the `CLIConfig` Pydantic model returned by `get_config()`, which raised `AttributeError: 'CLIConfig' object has no attribute 'get'`.

Replaced all 10 `config.get()` calls in `watcher.py`:
- `config.get("vault_path", ...)` → `config.vault.default_path` (typed attribute, consistent with `utils.py` and `init.py`)
- Gmail credentials, WhatsApp port/token, filesystem watch_path → used hardcoded defaults directly (these per-watcher settings have no corresponding fields in `CLIConfig`; the `.get()` defaults were already the only source of truth)

## Outcome

- ✅ Impact: 3 previously-failing CLI tests now pass. Full project suite green: 927 passed, 10 skipped, 0 failed.
- 🧪 Tests: 927 passed, 10 skipped. No regressions in any module (cli, watchers, logging, integration, performance).
- 📁 Files: 1 source file fixed (src/cli/watcher.py — 10 config.get() calls replaced).
- 🔁 Next prompts: All known test failures are resolved. Remaining warnings are `datetime.utcnow()` deprecations in `checkpoint.py` (cosmetic, Python 3.12 deprecation).
- 🧠 Reflection: The `config.get()` pattern is a common mistake when `get_config()` returns a typed Pydantic model rather than a plain dict. The project has an established pattern (`config.vault.default_path` in `utils.py:49` and `init.py:53`) that should be followed by all CLI commands. Per-watcher settings (gmail credentials path, whatsapp port/token) are not modeled in `CLIConfig` — they should either be added as typed fields or consistently sourced from env vars.

## Evaluation notes (flywheel)

- Failure modes observed: (1) dict `.get()` API called on Pydantic BaseModel — raises AttributeError at runtime, not caught at import time; (2) per-watcher config keys ("whatsapp_port", "gmail_credentials") referenced via config.get() but never defined in CLIConfig schema
- Graders run and results (PASS/FAIL): 927 PASS, 10 SKIP
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add WhatsAppConfig and GmailConfig sub-models to CLIConfig so per-watcher settings are typed and discoverable, rather than relying on env-var fallbacks.
