import requests
import urllib3

from .config import env

urllib3.disable_warnings()

ROUTES = [("0.0.0.0/0", "192.168.10.254"), ("10.10.0.0/16", "192.168.10.253")]


class Device:
    def __init__(self, host=None):
        self.host = host or env("DEVICE_HOST")
        self.root = f"{env('DEVICE_SCHEME', 'https')}://{self.host}"
        self.session = requests.Session()
        self.session.auth = (env("DEVICE_USER"), env("DEVICE_PASSWORD"))
        self.session.verify = env("DEVICE_VERIFY_TLS", "false").lower() == "true"
        self.create_verb = env("DEVICE_CREATE_VERB", "POST")

    def call(self, method, path, prefix="rest", **kwargs):
        response = self.session.request(method, f"{self.root}/{prefix}/{path}", timeout=5, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None

    def list(self, path):
        return self.call("GET", path)

    def create(self, path, payload):
        return self.call(self.create_verb, path, json=payload)

    def update(self, path, item_id, payload):
        return self.call("PATCH", f"{path}/{item_id}", json=payload)

    def delete(self, path, item_id):
        return self.call("DELETE", f"{path}/{item_id}")

    def ensure(self, path, payload, keys):
        for item in self.list(path):
            if all(item.get(k) == payload[k] for k in keys):
                return item, False
        return self.create(path, payload), True


def crud_demo(device):
    address = "192.168.20.1/24"
    created = device.create("ip/address", {"address": address, "interface": "ether2"})
    item_id = created[".id"]
    found = [a for a in device.list("ip/address") if a["address"] == address]
    patched = device.update("ip/address", item_id, {"comment": "TP5"})
    device.delete("ip/address", item_id)
    return [
        (device.create_verb, "ip/address", f"créée ({item_id})"),
        ("GET", "ip/address", f"{len(found)} trouvée(s)"),
        ("PATCH", f"ip/address/{item_id}", f"comment = {patched.get('comment')}"),
        ("DELETE", f"ip/address/{item_id}", "supprimée"),
    ]


def ensure_routes(device, routes=ROUTES):
    rows = []
    for destination, gateway in routes:
        payload = {"dst-address": destination, "gateway": gateway}
        _, created = device.ensure("ip/route", payload, ["dst-address", "gateway"])
        rows.append((destination, gateway, "créée" if created else "déjà présente"))
    return rows
