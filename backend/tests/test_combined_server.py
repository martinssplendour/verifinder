import pytest

from combined_server import _port, _run_setup


def test_port_uses_default_when_environment_is_missing(monkeypatch):
    monkeypatch.delenv("VERIFINDER_TEST_PORT", raising=False)
    assert _port("VERIFINDER_TEST_PORT", 8123) == 8123


@pytest.mark.parametrize("value", ["0", "65536", "not-a-port"])
def test_port_rejects_invalid_values(monkeypatch, value):
    monkeypatch.setenv("VERIFINDER_TEST_PORT", value)
    with pytest.raises(ValueError):
        _port("VERIFINDER_TEST_PORT", 8123)


def test_setup_bootstraps_parquet_and_billing_databases(monkeypatch):
    commands = []
    monkeypatch.setenv("PUBLIC_DATA_MODE", "parquet")
    monkeypatch.setattr("combined_server.subprocess.run", lambda command, **kwargs: commands.append(command))

    _run_setup()

    assert commands[0][-2:] == ["app.public_data_lake", "bootstrap"]
    assert commands[1][-4:] == ["-c", "billing_alembic.ini", "upgrade", "head"]


def test_setup_rejects_unknown_public_data_mode(monkeypatch):
    monkeypatch.setenv("PUBLIC_DATA_MODE", "unknown")

    with pytest.raises(ValueError, match="PUBLIC_DATA_MODE"):
        _run_setup()
