from uuid import uuid4

from app.platform.experiments import ExperimentManifest, ExperimentResult, read_experiment, write_experiment
from app.platform.registry import compatible_video_providers, list_providers
from app.orchestrator.media_strategy import VideoCapability


def test_provider_registry_is_versioned_and_local_only() -> None:
    providers = list_providers()
    assert providers
    assert all(item.version for item in providers)
    assert all(item.local_only for item in providers)


def test_video_compatibility_filters_capabilities() -> None:
    capability = VideoCapability(
        image_motion=False,
        image_to_video=True,
        text_to_video=False,
        max_duration_seconds=20,
        memory_class="high",
    )
    providers = compatible_video_providers(capability)
    assert [item.name for item in providers] == ["ltx_video"]


def test_experiment_manifest_round_trip(tmp_path) -> None:
    experiment = ExperimentManifest(name="smoke", provider="ltx_video", parameters={"steps": 8}, seed=7)
    result = ExperimentResult(experiment_id=experiment.id, status="completed", measurements={"latency": 1.2})
    write_experiment(tmp_path, experiment, result)
    payload = read_experiment(tmp_path, experiment.id)
    assert payload["manifest"]["id"] == str(experiment.id)
    assert payload["result"]["measurements"]["latency"] == 1.2
    assert experiment.id == UUID(payload["manifest"]["id"])
