import requests

from .config import env

NULL_SESSION = "0" * 32


class Ubus:
    def __init__(self, host=None):
        host = host or env("DEVICE_HOST")
        self.url = f"{env('DEVICE_SCHEME', 'http')}://{host}/ubus"
        self.session = NULL_SESSION

    def call(self, obj, method, args=None):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "call",
            "params": [self.session, obj, method, args or {}],
        }
        response = requests.post(self.url, json=payload, timeout=5)
        response.raise_for_status()
        result = response.json()["result"]
        if result[0] != 0:
            raise RuntimeError(f"ubus {obj}.{method} : code {result[0]}")
        return result[1] if len(result) > 1 else {}

    def login(self):
        credentials = {"username": env("UBUS_USER", "root"), "password": env("UBUS_PASSWORD")}
        self.session = self.call("session", "login", credentials)["ubus_rpc_session"]

    def lan_address(self):
        dump = self.call("network.interface", "dump")
        lan = next(i for i in dump["interface"] if i["interface"] == "lan")
        return lan["ipv4-address"][0]["address"]

    def set_lan_address(self, address):
        self.call("uci", "set", {"config": "network", "section": "lan", "values": {"ipaddr": address}})
        self.call("uci", "commit", {"config": "network"})


def demo(new_address="192.168.2.1"):
    ubus = Ubus()
    ubus.login()
    before = ubus.lan_address()
    ubus.set_lan_address(new_address)
    after = ubus.lan_address()
    return [
        ("session.login", "ubus_rpc_session obtenu"),
        ("network.interface.dump", f"lan = {before}"),
        ("uci.set + uci.commit", f"lan = {new_address}"),
        ("network.interface.dump", f"lan = {after}"),
    ]
