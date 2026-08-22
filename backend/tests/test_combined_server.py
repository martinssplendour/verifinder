import pytest

from combined_server import _port


def test_port_uses_default_when_environment_is_missing(monkeypatch):
    monkeypatch.delenv("VERIFINDER_TEST_PORT", raising=False)
    assert _port("VERIFINDER_TEST_PORT", 8123) == 8123


@pytest.mark.parametrize("value", ["0", "65536", "not-a-port"])
def test_port_rejects_invalid_values(monkeypatch, value):
    monkeypatch.setenv("VERIFINDER_TEST_PORT", value)
    with pytest.raises(ValueError):
        _port("VERIFINDER_TEST_PORT", 8123)
