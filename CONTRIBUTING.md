# Contributing

Thanks for helping improve Codex Usage Taskbar.

## Development setup

The project targets Windows and Python 3.12 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Run the test suite with Qt's headless platform:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q src tests
```

To verify the portable build:

```powershell
.\build.ps1
```

The executable is written to `dist\CodexUsageTaskbar\CodexUsageTaskbar.exe` and is intentionally ignored by Git.

## Pull requests

- Keep changes focused and explain the user-facing effect.
- Add or update tests for behavior changes.
- Do not include `.venv`, `build`, `dist`, generated `*.spec` files, local configuration, credentials, tokens, or account data.
- Keep version changes and `CHANGELOG.md` entries together when preparing a release.
- GitHub Actions must pass before a pull request is merged.

## Release process

The project uses semantic versions in `pyproject.toml`. A release tag must match the project version, for example `0.1.0` with tag `v0.1.0`. Pushing a matching tag starts the Windows packaging workflow and creates the GitHub release.
