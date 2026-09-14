from app.config import load_config


def test_config_is_local_only_by_default() -> None:
    config = load_config()
    assert config.runtime.local_only is True
    assert config.runtime.max_concurrent_media_jobs == 1
    assert config.llm.provider == "ollama"


def test_config_has_safe_storage_root() -> None:
    config = load_config()
    assert str(config.storage.root) == "data"


def test_config_has_local_image_defaults() -> None:
    config = load_config()
    assert config.image.provider == "diffusers"
    assert config.image.device == "mps"
    assert config.image.width == 1024
    assert config.image.height == 576
