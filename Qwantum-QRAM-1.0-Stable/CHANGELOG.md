# Changelog

## 1.0.0 — Stable
- Promoted the validated release candidate to stable version 1.0.0.
- Finalized API/version metadata and the browser UI release label.
- Retained versioned SQLite migrations, experiment audit history, optional API-key enforcement, process-local rate limiting, and the optional Qiskit Aer bridge.
- Regression suite passes: 32 tests.

## 1.0.0-rc1
- Added versioned SQLite migrations and legacy-database preservation tests.
- Added experiment metadata and durable lifecycle audit events.
- Added experiment event-history API.
- Added configurable API-key enforcement and process-local API rate limiting.
- Added session-scoped API-key support in the browser UI.
- Added release-candidate documentation and security/deployment caveats.
- Added fail-fast handling for databases whose schema version is newer than the application supports.
- Removed the known placeholder API secret from `.env.example`; API key is blank until explicitly configured.
