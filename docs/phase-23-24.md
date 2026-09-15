# Phases 23–24 — V2/V3 Product Evolution

## Phase 23 — V2 Advanced Production Features

### Objective
Move the V1 local video pipeline from a single-project generation workflow toward a robust production workstation without weakening the local-only architecture.

### Workstreams

1. **Project lifecycle and reproducibility**
   - Immutable generation manifests for every render.
   - Reproducible seed/model/provider configuration capture.
   - Project export/import for complete local archives.
   - Artifact integrity hashes and manifest verification.

2. **Generation orchestration**
   - Explicit job dependency graph for planning, image, audio, I2V, render and evaluation.
   - Resumable checkpoints at scene/artifact granularity.
   - Resource-aware scheduling for Apple Silicon unified memory.
   - Cancellation and graceful shutdown semantics.

3. **Advanced media controls**
   - Per-scene regeneration and timeline replacement.
   - Scene ordering and duration editing.
   - Voice/narration variants.
   - Configurable transition and subtitle styles.

4. **Evaluation and refinement**
   - Local model-based semantic evaluator behind a provider boundary.
   - Reference-image and continuity evaluation.
   - Automated bounded refinement proposals.
   - Final-video perceptual/technical scoring.

5. **Operational UI**
   - Scene-level status and artifact inspection.
   - Job dependency visualization.
   - Resource and timing dashboard.
   - Human approval checkpoints before expensive generation stages.

6. **Reliability and diagnostics**
   - Structured event log per project/job.
   - Failure classification and recovery recommendations.
   - Disk/cache lifecycle management.
   - Crash-safe cleanup and restart recovery.

### Constraints

- Remain local-only by default.
- No cloud inference or automatic uploads.
- Heavy model dependencies remain optional for CI.
- No unbounded retries or autonomous destructive operations.
- Target-machine acceptance remains mandatory for model/runtime behavior.

### Acceptance criteria

- Full project export/import preserves reproducibility metadata and artifacts.
- Interrupted jobs resume from the latest valid checkpoint.
- Scene-level regeneration does not invalidate unrelated artifacts.
- Local evaluator can score a project without network access.
- UI exposes job/resource state without requiring log inspection.
- CI covers deterministic orchestration and persistence behavior.
- M4 acceptance demonstrates resource-aware scheduling on real hardware.

## Phase 24 — V3 Platform Evolution / Research

### Objective
Establish a research-ready local platform while preserving deterministic orchestration and provider isolation.

### Workstreams

1. **Provider ecosystem**
   - Versioned provider capability contracts.
   - Pluggable local image, video, audio and evaluator backends.
   - Model compatibility and capability discovery.
   - Provider benchmark registry stored locally.

2. **Advanced local intelligence**
   - Multi-stage planning and critique loops.
   - Local storyboard and shot optimization.
   - Temporal consistency research integrations.
   - Optional local multimodal evaluation.

3. **Performance research**
   - Memory-aware batching and scheduling.
   - Model quantization/precision experiments.
   - M4 performance profiles and benchmark history.
   - Thermal-aware workload adaptation where supported.

4. **Research reproducibility**
   - Experiment manifests and dataset-free benchmark fixtures.
   - Deterministic seed/config capture.
   - Side-by-side provider/model comparisons.
   - Local experiment reports.

5. **Platform architecture**
   - Stable public internal APIs for providers and jobs.
   - Migration/versioning strategy beyond schema 1.1.
   - Local plugin boundary with explicit capability permissions.
   - Backward-compatible project formats where practical.

### Constraints

- Research features must remain isolated from the V1/V2 stable path.
- Locality/security invariants cannot be bypassed by plugins or providers.
- Experiments must be reproducible and auditable.
- Hardware-specific claims must come from target-machine evidence.

### Acceptance criteria

- Providers can be added without modifying core orchestration contracts.
- Benchmark runs produce comparable machine-readable reports.
- Experimental features can be enabled independently of the stable path.
- Schema/API evolution remains migration-safe.
- No research feature introduces mandatory network access.

## Sequencing

Phase 23 is the next implementation target. Phase 24 begins after the Phase 23 architecture is stable enough to provide extension points. Both phases require implementation documents, deterministic CI coverage where applicable, and explicit M4 acceptance for hardware-dependent behavior.
