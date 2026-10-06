# Preserve evidence when opening a Mem0 plugin store fails

**Zero × Youngseok Oh**

## Completed experiment, 6 October 2026

[Actual results and original artifact](RESULTS.md) · [Completed run 37404960619](https://github.com/YS-OH-CORE/second-paddle-notes/actions/runs/37404960619).

All eight specified observations completed: four scenarios on the original constructor and on an experimental discriminator. Under a real exclusive lock or a synthetic healthy-schema conflict, the original constructor returned with an empty active queue while the parked database retained its queued event. The discriminator surfaced the error and preserved the queue. Normal opening and the explicit non-database fixture retained their expected behavior. This is an executed Linux diagnostic, not a finished recovery patch, a Windows reproduction or upstream adoption. The original artifact was downloaded and its digest, CRC, eight individual logs and source hashes checked. This documentation-only update does not start another run.

## Scope and reproduction

A bounded follow-up to Storres1970's report [mem0ai/mem0#7549](https://github.com/mem0ai/mem0/issues/7549), investigating only the first reported problem. The original Windows observations belong to that author.

This script downloads and verifies the complete pinned memory_core module and telemetry source at `c93420c49a6b14c3d446bdb156d96811908fd90a`. It compares the real EvidenceStore constructor with a narrow experimental error-code classifier, using fresh child processes and real temporary SQLite files. The four scenarios per variant are normal open, an actual exclusive lock, a structurally healthy database whose view conflicts with the legacy DROP TABLE migration, and a deliberately non-database fixture. Only disabled telemetry is replaced by an in-memory observer. Probe processes reject network connection attempts.

The classifier propagates errors other than primary SQLITE_CORRUPT/SQLITE_NOTADB. It is **not a complete safe-recovery design**: backup/rename failures, corruption rechecks, concurrent replacement and all crash cases need separate decisions. It does not address the report's API-key cache race or stdin decoding. It does not run Claude hooks, the remote memory backend, or Windows.

A successful job means all specified behavioral observations held, including reproducing the undesirable baseline behavior. It does not mean the baseline is correct, every plugin test passed, or a patch was accepted. No release, upstream PR, portfolio promotion, user memory or credential is involved.

Run with Python 3.11+ in a new working directory: `python compare.py`. No third-party Python package is installed. Public source downloads are bounded and Git-blob checked; the original Mem0 license is retained. One standard Linux job with a five-minute cap, no schedule, is configured on this separate verification branch.

AI assistance: Zero prepared the probes and performed analysis under Youngseok Oh's direction. These are not independent human reruns. Original source remains the work of Mem0 contributors under its license. New wrapper code is provided under Apache-2.0; original notices are retained in the downloaded LICENSE.mem0. No endorsement is implied.
