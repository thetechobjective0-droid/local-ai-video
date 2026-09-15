from app.observability import PipelineMetrics


def test_metrics_collect_counters_and_duration_summary() -> None:
    metrics = PipelineMetrics()
    metrics.increment("images")
    metrics.increment("images", 2)
    metrics.observe("image_generation", 1.0)
    metrics.observe("image_generation", 3.0)

    snapshot = metrics.snapshot()

    assert snapshot["counters"]["images"] == 3
    assert snapshot["durations_seconds"]["image_generation"]["count"] == 2
    assert snapshot["durations_seconds"]["image_generation"]["average"] == 2.0
