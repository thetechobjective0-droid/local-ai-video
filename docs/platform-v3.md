# V3 Platform Layer

The V3 layer is implemented as local-only extension contracts around the stable generation pipeline.

## Provider registry

`app/platform/registry.py` exposes versioned provider descriptors, capability discovery, and compatibility filtering without changing the core provider implementations.

## Benchmarks

`app/platform/benchmarks.py` stores machine-readable memory/disk/environment measurements under the local storage root. No network telemetry is used.

## Experiments

`app/platform/experiments.py` stores reproducible provider/version/parameter/seed manifests and local result measurements. Experiment records are JSON and remain inside local storage.

## HTTP surface

`app/platform_api.py` exposes provider discovery, video compatibility, benchmark creation/history, and experiment lifecycle endpoints through the loopback FastAPI application.

Research-specific model integrations remain optional: the platform records and compares experiments without making any external service mandatory.
