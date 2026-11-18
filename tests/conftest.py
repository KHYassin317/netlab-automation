import pytest

from netlab import mock


@pytest.fixture
def lab(monkeypatch, tmp_path):
    server, state = mock.start()
    host = f"127.0.0.1:{server.server_address[1]}"
    values = {
        "DEVICE_SCHEME": "http",
        "DEVICE_HOST": host,
        "DEVICE_USER": "api-user",
        "DEVICE_PASSWORD": "lab-pass",
        "DEVICE_CREATE_VERB": "POST",
        "UBUS_USER": "root",
        "UBUS_PASSWORD": "openwrt",
        "SOAR_LOG": str(tmp_path / "soar.log"),
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    yield host
    server.shutdown()
