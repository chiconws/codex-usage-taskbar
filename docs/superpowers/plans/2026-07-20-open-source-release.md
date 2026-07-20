# Open-Source Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Turn the existing Windows Codex usage widget into a clean public MIT repository with tested CI and a downloadable `v0.1.0` release.

**Architecture:** Keep the application source and packaging model intact. Add repository metadata and Windows GitHub Actions workflows: CI validates pull requests and `main`, while the release workflow validates a semantic-version tag, builds the portable executable, and attaches a zip to the GitHub release.

**Tech Stack:** Git, GitHub CLI, GitHub Actions, Windows Server 2025 runner, Python 3.12/3.13, PySide6, pytest, PyInstaller, PowerShell.

## Global Constraints

- Public repository target: `chiconws/codex-usage-taskbar`.
- License: MIT.
- Initial project version and release tag: `0.1.0` and `v0.1.0`.
- Commit author label: `Codex`; authenticated GitHub account remains `chiconws`.
- Never publish `.venv`, `build`, `dist`, caches, bytecode, generated `*.spec`, `.superpowers`, or user profile configuration.
- CI and release jobs run on Windows.
- Release publication occurs only for explicit `v*.*.*` tags.

---

### Task 1: Publishable repository boundary and project documentation

**Files:**
- Modify: `.gitignore`
- Create: `LICENSE`
- Create: `CONTRIBUTING.md`
- Create: `SECURITY.md`
- Create: `CHANGELOG.md`
- Modify: `README.md`

**Interfaces:**
- Produces the public repository policy consumed by contributors and GitHub workflows.

- [ ] **Step 1: Add publication exclusions**

Add `.superpowers/`, coverage output, and local release archives to `.gitignore` while retaining the existing generated-file exclusions.

- [ ] **Step 2: Add the MIT license**

Add the complete MIT text with copyright holder `CodexUsageTaskbar contributors` and year `2026`.

- [ ] **Step 3: Add contributor and security guidance**

Document the Windows development commands, test command, branch/PR expectations, supported version floor, and the rule that users must never submit Codex account data, tokens, or local configuration. State that security reports should use private GitHub contact channels when available.

- [ ] **Step 4: Add the initial changelog and public README details**

Record `0.1.0` as the initial release and add public installation, development, testing, packaging, and release links without exposing local machine paths.

- [ ] **Step 5: Review text for private data**

Run `rg -n --hidden` excluding generated directories and confirm no machine-specific `C:\Users\<username>` path, credential-like value, or real email is present in the files being added.

- [ ] **Step 6: Commit documentation and boundary changes**

Run:

```powershell
git add .gitignore LICENSE CONTRIBUTING.md SECURITY.md CHANGELOG.md README.md
git commit -m "docs: prepare project for open-source release"
```

Expected result: one commit containing only public repository policy and documentation.

### Task 2: Windows CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes `pyproject.toml`, `build.ps1`, and the existing test suite.
- Produces a required GitHub check named `test` for pushes and pull requests targeting `main`.

- [ ] **Step 1: Define Windows test matrix**

Use `windows-latest` with Python `3.12` and `3.13`, trigger on `pull_request` and `push` to `main`, and set `QT_QPA_PLATFORM=offscreen`.

- [ ] **Step 2: Install and test**

Upgrade pip, install `.[dev]`, run `python -m pytest -q`, run `python -m compileall -q src tests`, and run `./build.ps1`.

- [ ] **Step 3: Validate the packaged executable**

Check that `dist/CodexUsageTaskbar/CodexUsageTaskbar.exe` exists and upload the packaged directory as a CI artifact.

- [ ] **Step 4: Commit CI**

Run `git add .github/workflows/ci.yml; git commit -m "ci: test and package on Windows"`.

Expected result: CI is deterministic, does not require Codex credentials, and produces a reviewable package artifact.

### Task 3: Tagged release workflow and version guard

**Files:**
- Create: `.github/workflows/release.yml`

**Interfaces:**
- Consumes explicit tags matching `v*.*.*` and the version in `pyproject.toml`.
- Produces a GitHub release with `CodexUsageTaskbar-vX.Y.Z-windows-x64.zip`.

- [ ] **Step 1: Add tag trigger and permissions**

Trigger only on `v*.*.*` tags, use a Windows runner, and grant `contents: write` to the job.

- [ ] **Step 2: Enforce version agreement**

Read the project version from `pyproject.toml` and fail unless it equals the tag without the leading `v`.

- [ ] **Step 3: Repeat verification and package**

Install `.[dev]`, run the offscreen tests and compile check, execute `build.ps1`, verify the executable, and zip the complete portable directory.

- [ ] **Step 4: Create the release**

Use the runner's authenticated GitHub CLI and `GITHUB_TOKEN` to create the release from the current tag and attach the zip.

- [ ] **Step 5: Commit release automation**

Run `git add .github/workflows/release.yml; git commit -m "ci: automate tagged Windows releases"`.

Expected result: a future `git push origin vX.Y.Z` creates one version-checked GitHub release.

### Task 4: Local verification and Git history

**Files:**
- Git metadata only: `.git/`

**Interfaces:**
- Consumes the reviewed working tree and produces a clean `main` history ready for remote publication.

- [ ] **Step 1: Initialize Git and configure the local author**

Run `git init -b main`, configure repository-local `user.name` to `Codex` and a neutral non-account author email, and confirm the configured values.

- [ ] **Step 2: Stage only the reviewed public tree**

Run `git status --short --ignored`, then stage explicit public paths. Confirm `.superpowers`, `.venv`, `build`, `dist`, caches, and `CodexUsageTaskbar.spec` are not staged.

- [ ] **Step 3: Run local checks**

Run the project test command with the repository virtual environment, the offscreen test command, `compileall`, and `build.ps1`. Keep any pre-existing local build outputs ignored.

- [ ] **Step 4: Create the initial source commit**

Commit the application and public release setup as `feat: publish Codex usage taskbar` after the checks pass.

Expected result: clean working tree, two or more intentional commits, and a packaged executable available locally.

### Task 5: GitHub repository, pull request, merge, and release

**Files:**
- Remote repository: `chiconws/codex-usage-taskbar`

**Interfaces:**
- Consumes local `main` and `agent/open-source-release` branches plus authenticated GitHub CLI access.
- Produces a public repository, merged pull request, `v0.1.0` tag, and downloadable GitHub release.

- [ ] **Step 1: Create the remote repository**

Use `gh repo create chiconws/codex-usage-taskbar --public --description ...` without adding a remote README or license that would conflict with the local history.

- [ ] **Step 2: Push the initial main branch**

Add `origin`, push `main`, create `agent/open-source-release` from it, and push that branch with tracking.

- [ ] **Step 3: Open and validate the pull request**

Create a draft pull request, wait for the Windows CI check, inspect the check result, then mark the pull request ready and merge it with a merge commit or squash only after CI is green.

- [ ] **Step 4: Tag and push `v0.1.0`**

Create an annotated tag with the initial release message and push it to `origin`.

- [ ] **Step 5: Verify the release**

Wait for the tagged release workflow, inspect its job and artifact, and confirm the public release contains the Windows zip and the expected executable path.

- [ ] **Step 6: Report the handoff**

Return the repository URL, PR URL, release URL, commit/tag identifiers, CI result, and any remaining limitation such as the app-server requiring a user's local Codex login.
