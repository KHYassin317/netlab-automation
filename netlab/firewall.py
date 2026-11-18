import ipaddress

import yaml

from .config import DATA, read

ACTIONS = {"accept", "drop", "reject"}
REQUIRED = {"name", "src", "dst", "proto", "port", "action"}


def load(name):
    return yaml.safe_load(read(DATA / "firewall" / name))


def lint(rules):
    errors = []
    for rule in rules:
        label = rule.get("name", "?")
        missing = REQUIRED - rule.keys()
        if missing:
            errors.append(f"{label} : champs manquants {sorted(missing)}")
            continue
        if rule["action"] not in ACTIONS:
            errors.append(f"{label} : action invalide '{rule['action']}'")
        for side in ("src", "dst"):
            if rule[side] != "any":
                try:
                    ipaddress.ip_network(rule[side], strict=False)
                except ValueError:
                    errors.append(f"{label} : {side} invalide '{rule[side]}'")
    return errors


def validate(rules):
    errors = []
    names = [r["name"] for r in rules]
    if len(names) != len(set(names)):
        errors.append("noms de règles dupliqués")
    for rule in rules:
        if rule["action"] == "accept" and rule["src"] == "any" and rule["dst"] == "any":
            errors.append(f"{rule['name']} : règle any-any interdite")
    if not rules or rules[-1]["action"] != "drop":
        errors.append("la dernière règle doit être un drop par défaut")
    return errors


def in_network(value, address):
    return value == "any" or ipaddress.ip_address(address) in ipaddress.ip_network(value, strict=False)


def matches(rule, flow):
    return (
        in_network(rule["src"], flow["src"])
        and in_network(rule["dst"], flow["dst"])
        and rule["proto"] in ("any", flow["proto"])
        and rule["port"] in ("any", flow["port"])
    )


def verdict(rules, flow):
    for rule in rules:
        if matches(rule, flow):
            return "accept" if rule["action"] == "accept" else "drop"
    return "drop"


def regression(rules, flows):
    failures = []
    for flow in flows:
        got = verdict(rules, flow)
        if got != flow["expect"]:
            failures.append(f"{flow['src']} -> {flow['dst']}:{flow['port']}/{flow['proto']} attendu {flow['expect']}, obtenu {got}")
    return failures


def deploy(device, rules):
    rows = []
    for rule in rules:
        payload = {"chain": "forward", "action": rule["action"], "comment": rule["name"]}
        if rule["src"] != "any":
            payload["src-address"] = rule["src"]
        if rule["dst"] != "any":
            payload["dst-address"] = rule["dst"]
        if rule["proto"] != "any":
            payload["protocol"] = rule["proto"]
        if rule["port"] != "any":
            payload["dst-port"] = str(rule["port"])
        _, created = device.ensure("ip/firewall/filter", payload, ["comment"])
        rows.append((rule["name"], "créée" if created else "déjà présente"))
    return rows


def pipeline(device=None, rules_file="rules.yaml"):
    rules = load(rules_file)["rules"]
    flows = load("flows.yaml")["flows"]
    stages = [
        ("lint", lambda: lint(rules)),
        ("validation", lambda: validate(rules)),
        ("tests de non-régression", lambda: regression(rules, flows)),
    ]
    report = []
    for name, check in stages:
        problems = check()
        report.append((name, "OK" if not problems else "ÉCHEC", "; ".join(problems)))
        if problems:
            return report, False
    if device is not None:
        deploy(device, rules)
        report.append(("déploiement", "OK", f"{len(rules)} règles appliquées"))
    return report, True
