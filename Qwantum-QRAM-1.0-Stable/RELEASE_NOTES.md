# Qwantum QRAM 1.0.0 — Stable Release Notes

## Summary
QRAM 1.0.0 is the stable release of the local-first QRAM software simulator after the 1.0 release candidate.

## Included
- SQLite-based addressable memory, revisions, and event history.
- Transactional SQLite schema migrations (schema version 3).
- Durable experiment records, metadata, results, and status history.
- Optional Qiskit Aer bridge for small circuit simulations.
- Optional API-key protection and process-local rate limiting.
- Browser-based management interface and FastAPI OpenAPI docs.
- Automated regression suite: 32 tests passed in the release environment.

## Known limits
- This is not physical QRAM or a physical 777-qubit device.
- QWP-777 and Nebiru adapters are contracts only; no live connection is included.
- API-key authentication is a single shared secret.
- The rate limiter is process-local.
- Qiskit Aer is an optional dependency and simulates circuits on classical hardware.

## Recommended deployment
Use localhost by default. For remote use, require a strong `QRAM_API_KEY`, use HTTPS via a trusted reverse proxy, configure proxy-side rate limits, keep `.env` private, and test database backup/restore before storing important data.
