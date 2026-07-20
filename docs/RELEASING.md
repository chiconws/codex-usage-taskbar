# Releasing

This project publishes Windows releases from explicit semantic-version tags.

## Prepare a release

1. Update `version` in `pyproject.toml`.
2. Add a matching entry to `CHANGELOG.md`.
3. Run the local checks from `CONTRIBUTING.md` and verify the portable build.
4. Commit the version and changelog changes and merge them into `main`.

The project version and tag must match. For example:

```text
pyproject.toml: version = "0.1.0"
Git tag:         v0.1.0
```

## Publish

Create and push an annotated tag from the merged `main` commit:

```powershell
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

The release workflow validates the version, runs the Windows test and compile checks, builds `CodexUsageTaskbar.exe`, creates a Windows x64 zip, and attaches it to the GitHub release.

Do not upload local configuration, Codex account data, credentials, tokens, `.venv`, `build`, `dist`, or generated PyInstaller specs.
