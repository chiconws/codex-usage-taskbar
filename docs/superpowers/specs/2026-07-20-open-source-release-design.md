# Open-Source Distribution and Release Design

**Date:** 2026-07-20

## Goal

Publish `codex-usage-taskbar` as a public MIT-licensed GitHub repository at `chiconws/codex-usage-taskbar`, with reproducible Windows CI, tagged versioning, and downloadable packaged releases.

## Approved decisions

- Repository visibility: public.
- Repository name: `codex-usage-taskbar` under the authenticated `chiconws` account.
- License: MIT.
- Initial version: `0.1.0`, released as tag `v0.1.0`.
- Commit display name: `Codex`; GitHub authentication and PR/release ownership remain the authenticated `chiconws` account and GitHub Actions bot.
- Default branch: `main`.
- Publication branch: `agent/open-source-release`, merged through a pull request after CI succeeds.
- Release artifacts: a Windows x64 zip containing the portable `CodexUsageTaskbar` build.

## Repository boundary

The public repository contains the application source, tests, README, packaging entrypoint, build script, icon assets, project metadata, license, contributor/security guidance, and GitHub workflow definitions. It excludes `.venv`, `build`, `dist`, caches, bytecode, generated PyInstaller specs, `.superpowers`, and any user profile configuration.

The project does not store Codex credentials, tokens, account configuration, or telemetry data in the repository. Test account values remain synthetic `example.com` data.

## Release architecture

GitHub Actions runs on Windows because the application and PyInstaller target Windows. Pull requests and pushes to `main` install the development extras, run the offscreen Qt test suite, compile the source, and run the packaging script. A tag matching `v*.*.*` repeats those checks, confirms the tag matches `pyproject.toml`, creates the portable build, zips it, and creates a GitHub release with the zip attached.

Versioning remains intentionally explicit in `pyproject.toml`; a release is valid only when the Git tag and project version agree. The first release is `v0.1.0`; later releases use normal semantic-version tags and changelog entries.

## Pull-request and release flow

1. Stage only reviewed project files on `agent/open-source-release`.
2. Commit the release infrastructure as a small set of logical commits.
3. Push the branch and open a pull request against `main`.
4. Wait for the Windows CI check, merge the pull request, and push `v0.1.0`.
5. Confirm the release workflow completes and the zip is downloadable.

No automatic release is created from ordinary pushes. Release publication requires an explicit version tag.

## Validation

Local validation uses the repository virtual environment and runs `pytest`, offscreen Qt tests, `compileall`, and `build.ps1`. CI repeats the same checks on a clean Windows runner. The release workflow additionally validates the project/tag version match and checks that the expected executable exists inside the packaged output.

## Known limitations

- GitHub commit attribution for the local `Codex` author label is not the same as a GitHub account identity; the authenticated account performs the push and owns the PR/release.
- The application remains a local Windows utility and has no cross-platform release artifact.
- GitHub Actions can validate the package but cannot exercise a real user's logged-in Codex app-server session.
