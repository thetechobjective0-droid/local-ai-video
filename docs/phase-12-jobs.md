# Phase 12 — Local Job Orchestration

## Purpose

Phase 12 moves long-running project media generation out of the HTTP request lifecycle while keeping the system local-first and thin at the web boundary.

## Implemented

- persistent JSON job manifests under the configured storage root in `jobs/`
- job states: `queued`, `running`, `completed`, `failed`, `interrupted`
- single local worker thread by default to bound Apple Silicon resource contention
- worker invokes the existing `generate_project_media` orchestration service; generation logic is not duplicated in the web layer
- atomic job-state persistence
- per-scene progress persisted as `completed_scenes / scene_count`
- process-restart detection marks stale queued/running jobs as `interrupted`
- local API endpoints for submitting, reading and listing media jobs
- browser dashboard control and 2-second status polling
- completed/failed/interrupted jobs automatically refresh project artifacts in the dashboard

## API

```text
POST /api/projects/{project_id}/jobs/media
GET  /api/jobs/{job_id}
GET  /api/projects/{project_id}/jobs
```

`POST` returns HTTP 202 and a durable job record. Generation continues in the local worker after the request returns.

## Restart semantics

The worker pool is intentionally process-local rather than a cloud queue or external broker. On application startup, persisted `queued` and `running` records from the previous process are marked `interrupted`. A user can submit a new job; the underlying media generation remains artifact-first and can reuse already persisted scene assets according to the existing orchestration rules.

## Resource policy

The default worker count is one. This avoids concurrent model execution and uncontrolled unified-memory pressure on the target Apple M4 / 36 GB configuration. Higher concurrency is deliberately deferred until hardware measurements justify it.

## Acceptance

Repository implementation is complete. Target-machine acceptance remains pending and must measure actual local model loading, unified-memory pressure, latency, thermal behavior, restart recovery and final media quality on the target Mac.
