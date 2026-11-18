import pytest
import requests

from netlab import netconf, restconf, rest, ubus


def test_crud(lab):
    rows = rest.crud_demo(rest.Device())
    assert [r[0] for r in rows] == ["POST", "GET", "PATCH", "DELETE"]
    assert rows[1][2] == "1 trouvée(s)"


def test_routes_idempotent(lab):
    device = rest.Device()
    first = rest.ensure_routes(device)
    second = rest.ensure_routes(device)
    assert {r[2] for r in first} == {"créée"}
    assert {r[2] for r in second} == {"déjà présente"}
    assert len(device.list("ip/route")) == len(rest.ROUTES)


def test_bad_password(lab, monkeypatch):
    monkeypatch.setenv("DEVICE_PASSWORD", "mauvais")
    with pytest.raises(requests.HTTPError):
        rest.Device().list("ip/address")


def test_ubus(lab):
    client = ubus.Ubus()
    with pytest.raises(RuntimeError):
        client.lan_address()
    client.login()
    client.set_lan_address("192.168.2.1")
    assert client.lan_address() == "192.168.2.1"


def test_restconf(lab):
    device = rest.Device()
    restconf.set_enabled(device, "GigabitEthernet2", True)
    assert restconf.interface(device, "GigabitEthernet2")["enabled"] is True
    assert len(restconf.interfaces(device)) == 2


def test_netconf_candidate_and_lock():
    stores = netconf.Datastores({"eth0": False})
    stores.lock("alice")
    stores.edit_config("alice", "eth0", True)
    assert stores.running["eth0"] is False
    with pytest.raises(RuntimeError):
        stores.edit_config("bob", "eth0", False)
    stores.commit("alice")
    assert stores.running["eth0"] is True


def test_netconf_xml():
    xml = (
        '<data><interfaces xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">'
        "<interface><name>eth0</name><enabled>true</enabled></interface></interfaces></data>"
    )
    assert netconf.parse_interfaces(xml) == {"eth0": True}
    assert "<candidate/>" in netconf.edit_config("eth0", True)
