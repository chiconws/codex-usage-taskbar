# Security policy

## Scope

Codex Usage Taskbar is a local Windows utility. It does not provide a network service, store Codex credentials, read `auth.json`, send telemetry, or intentionally collect account data beyond displaying fields returned by the locally installed Codex app-server.

## Reporting a vulnerability

Please do not publish credentials, account identifiers, tokens, screenshots containing private information, or exploit details in a public issue. Use GitHub's private vulnerability reporting for this repository when available. If it is unavailable, contact a repository maintainer through a private GitHub channel before disclosure.

Include the affected version, Windows/Python details, reproduction steps that do not contain private data, and the expected versus actual behavior.

## Release hygiene

Never commit user profile configuration, `.venv`, `build`, `dist`, generated PyInstaller specs, caches, or local logs. The application may display live account metadata on the user's machine; that data must not be included in bug reports without redaction.
