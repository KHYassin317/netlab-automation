def service_disabled(name):
    def check(device):
        service = next((s for s in device.list("ip/service") if s["name"] == name), None)
        return service is None or service["disabled"] == "true"

    return check


def no_default_admin(device):
    return all(user["name"] != "admin" for user in device.list("user"))


def has_final_drop(device):
    rules = device.list("ip/firewall/filter")
    return bool(rules) and rules[-1].get("action") == "drop"


CHECKS = [
    ("C1", "Service telnet désactivé", "élevée", service_disabled("telnet")),
    ("C2", "Service ftp désactivé", "élevée", service_disabled("ftp")),
    ("C3", "Service www (HTTP en clair) désactivé", "moyenne", service_disabled("www")),
    ("C4", "Compte admin par défaut supprimé", "moyenne", no_default_admin),
    ("C5", "Règle drop finale dans le pare-feu", "élevée", has_final_drop),
]


def audit(device):
    return [(cid, title, level, "OK" if check(device) else "NON CONFORME") for cid, title, level, check in CHECKS]


def remediate(device):
    fixed = []
    for service in device.list("ip/service"):
        if service["name"] in ("telnet", "www") and service["disabled"] != "true":
            device.update("ip/service", service[".id"], {"disabled": "true"})
            fixed.append(service["name"])
    return fixed


def blocking(results):
    return [r for r in results if r[2] == "élevée" and r[3] != "OK"]


def report(host, results):
    lines = [f"# Rapport de conformité : {host}", "", "| ID | Contrôle | Criticité | Résultat |", "|---|---|---|---|"]
    lines += [f"| {c} | {t} | {level} | {r} |" for c, t, level, r in results]
    return "\n".join(lines) + "\n"
