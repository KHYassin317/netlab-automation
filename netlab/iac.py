from concurrent.futures import ThreadPoolExecutor

import yaml
from jinja2 import Environment, FileSystemLoader

from .config import DATA, read
from .rest import Device

SPECS = {
    "ip/address": ("addresses", ["address", "interface"]),
    "ip/route": ("routes", ["dst-address", "gateway"]),
}


def inventory():
    return yaml.safe_load(read(DATA / "inventory.yaml"))["hosts"]


def render(name, host):
    loader = FileSystemLoader(str(DATA / "templates"))
    templates = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
    return templates.get_template(f"{host['platform']}.j2").render(name=name, **host)


def key(item, fields):
    return tuple(item.get(f) for f in fields)


def diff(device, host):
    result = {"missing": [], "extra": []}
    for path, (field, keys) in SPECS.items():
        wanted = {key(i, keys): i for i in host.get(field, [])}
        actual = {key(i, keys): i for i in device.list(path) if i.get("dynamic") != "true"}
        result["missing"] += [(path, item) for k, item in wanted.items() if k not in actual]
        result["extra"] += [(path, item) for k, item in actual.items() if k not in wanted]
    return result


def apply(device, host, prune=False):
    actions = []
    changes = diff(device, host)
    for path, item in changes["missing"]:
        device.create(path, item)
        actions.append(("créé", path, key(item, SPECS[path][1])))
    if prune:
        for path, item in changes["extra"]:
            device.delete(path, item[".id"])
            actions.append(("supprimé", path, key(item, SPECS[path][1])))
    return actions


def run_parallel(task, hosts):
    def one(name):
        return name, task(Device(hosts[name]["hostname"]), hosts[name])

    with ThreadPoolExecutor(max_workers=len(hosts)) as pool:
        return dict(pool.map(one, hosts))
