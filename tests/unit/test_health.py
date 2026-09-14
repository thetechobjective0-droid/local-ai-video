from app.health import check_command, check_platform


def test_platform_check_returns_result() -> None:
    result = check_platform()
    assert result.name == "apple_silicon"
    assert isinstance(result.ok, bool)
    assert result.detail


def test_existing_python_command_is_detected() -> None:
    result = check_command("python")
    assert result.name == "python"
    assert result.ok is True
