from .rest import Device

HEADERS = {"Accept": "application/yang-data+json", "Content-Type": "application/yang-data+json"}
PREFIX = "restconf/data"
MODULE = "ietf-interfaces:interfaces"


def interfaces(device):
    reply = device.call("GET", MODULE, prefix=PREFIX, headers=HEADERS)
    return reply[MODULE]["interface"]


def interface(device, name):
    reply = device.call("GET", f"{MODULE}/interface={name}", prefix=PREFIX, headers=HEADERS)
    return reply["ietf-interfaces:interface"]


def set_enabled(device, name, enabled):
    body = {"ietf-interfaces:interface": {"name": name, "enabled": enabled}}
    device.call("PATCH", f"{MODULE}/interface={name}", prefix=PREFIX, headers=HEADERS, json=body)


def demo(device=None, name="GigabitEthernet2"):
    device = device or Device()
    before = interface(device, name)["enabled"]
    set_enabled(device, name, not before)
    after = interface(device, name)["enabled"]
    return [
        ("GET", f"{MODULE}/interface={name}", f"enabled = {before}"),
        ("PATCH", f"{MODULE}/interface={name}", f"enabled = {not before}"),
        ("GET", f"{MODULE}/interface={name}", f"enabled = {after}"),
    ]
