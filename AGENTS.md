# Repository Guidelines

## Project Structure & Module Organization
- `agent.py` — Core AI agent (pydantic-ai + GitHub Models) and types.
- `app/cli.py` — CLI entry to process a local receipt image.
- `app/main.py` — FastAPI webhook for Telegram bot, ngrok helper.
- `pyproject.toml` — Python 3.12+, dependencies (managed with `uv`).
- `render.yaml` — Render.com service configuration.
- Add tests under `tests/` (e.g., `tests/test_agent.py`).

## Build, Test, and Development Commands
- Install deps: `uv sync` (add `--group dev` for ngrok tooling).
- Run CLI: `uv run receipt-agent path/to/receipt.jpg` (or `uv run python -m app.cli path/to/receipt.jpg`).
- Run webhook (auto-ngrok): `USE_NGROK=true uv run uvicorn app.main:app --reload`.
- Health check: `curl http://127.0.0.1:8000/healthz`.
- Deploy (Render): uses `render.yaml` with `uv sync --frozen` and `uvicorn`.

## Coding Style & Naming Conventions
- Python only; use type hints and docstrings for public functions/classes.
- Indentation: 4 spaces; prefer explicit returns and early exits.
- Naming: `snake_case` for functions/vars, `PascalCase` for classes, `UPPER_SNAKE` for constants, module files `snake_case.py`.
- Imports: standard lib → third‑party → local; avoid wildcard imports.
- Logging over `print`; avoid side effects at import time.

## Testing Guidelines
- Framework: pytest (add under `tests/` as `test_*.py`).
- Run tests: `uv run pytest -q`.
- Recommendations: mock network calls (Telegram, model provider); use `httpx.AsyncClient` for FastAPI route tests; aim for ≥80% coverage if adding `pytest-cov`.

## Commit & Pull Request Guidelines
- Commits: concise, imperative subject (≤72 chars). Conventional prefixes encouraged: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`.
- PRs: clear description, linked issue(s), reproduction steps, screenshots or logs when relevant. Include what changed, why, and how to verify.
- Ensure: tests updated/added, docs touched when behavior changes, no secrets or tokens in code, logs, or diffs.

## Security & Configuration Tips
- Create `.env` from `.env.copy`; do not commit `.env` or credentials.
- Required env: `GITHUB_API_KEY`, `TELEGRAM_BOT_TOKEN`; optional: `TELEGRAM_BOT_SECRET_TOKEN`, `USE_NGROK`, `RENDER`, `RENDER_EXTERNAL_URL`.
- Never embed secrets in code or tests; prefer env vars and local `.env`.
