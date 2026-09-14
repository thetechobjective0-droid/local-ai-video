# Phase 9 — Quality Assurance

## Status

**IN PROGRESS — 9.1 QA CLI AND TARGETED REGENERATION**

Phase 9 now has deterministic media/project validators plus a project-level QA command and targeted scene regeneration workflow.

## Implemented in 9.1

- `video-agent qa <PROJECT_ID>` runs project QA and persists `qa-report.json`.
- QA reports are machine-readable with a schema version, pass/fail status, and actionable scope/message failures.
- QA output identifies the exact scene or project artifact associated with a failure.
- `video-agent regenerate-scene <PROJECT_ID> <SCENE_ID>` supports targeted `image`, `audio`, `video`, or `all` regeneration.
- Regeneration invalidates the affected persisted artifact before generation so stale cache entries cannot silently satisfy a requested video regeneration.
- Regenerating an image also invalidates its dependent scene video.
- QA is rerun after targeted regeneration and a fresh `qa-report.json` is persisted.

## Commands

```bash
uv run video-agent qa <PROJECT_ID>
uv run video-agent regenerate-scene <PROJECT_ID> <SCENE_ID> --stage video
```

## Next

1. Audio loudness and silence QA.
2. Final render QA gate.
3. Semantic/visual quality checks where practical.
4. M4 hardware acceptance and performance measurements.
