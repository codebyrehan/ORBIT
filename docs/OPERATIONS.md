# ORBIT Operations Runbook

## Release gate

Every release is expected to pass the `Production Release Gate` workflow in addition to the existing CI, Security E2E, Container Smoke, and Recovery E2E workflows.

The gate covers:

- authentication regression
- rate limiting and `Retry-After`
- observability and audit endpoint contracts
- durable-state backup with SHA-256 verification
- restore into a clean state and application readback
- SIGTERM shutdown and restart
- final endpoint and concurrency regression sweep

## State backup

Back up the ORBIT data directory with:

```bash
./scripts/backup_data.sh /var/lib/orbit ./backups
```

The helper creates a timestamped `tar.gz` archive and a matching `.sha256` manifest.

## State restore

Restore a verified archive into a clean directory with:

```bash
./scripts/restore_data.sh ./backups/orbit-data-<timestamp>.tar.gz /var/lib/orbit
```

If a `.sha256` manifest is present next to the archive, the restore helper verifies it before extraction.

For a container bind mount, the restored directory and files must be writable by the service user. The production image runs as the non-root `orbit` user (UID 10001).

## Shutdown

Use a graceful SIGTERM first. Uvicorn handles the signal and exits normally; the persistent journal remains available for restart/recovery.

```bash
docker kill --signal=TERM orbit-production
```

Do not use `SIGKILL` as the normal shutdown path because it bypasses application/server cleanup.

## Health checks

Public readiness checks:

```text
/health
/ready
```

The production deployment uses the Render service `orbit-production` on the `foundation` branch.

## Observability

Authenticated metrics:

```text
GET /v1/metrics
```

The metrics contract exposes request totals, failures, token totals, latency totals/average, and error rate. Audit records are available through:

```text
GET /v1/audit/events
```

## Rollback

If a release passes CI but fails live validation, keep the last known-good deployment available in Render and roll the service back to that deployment before investigating the new revision. Do not overwrite the known-good state while debugging a production incident.

## Production invariant

A release is not considered complete until all five conditions hold:

1. backup/restore succeeds
2. graceful shutdown/restart succeeds
3. observability contracts remain valid under workload
4. the combined regression gate is green
5. the deployed revision is live and matches the tested commit
