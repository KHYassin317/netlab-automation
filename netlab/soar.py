import json
import time

import yaml

from .config import DATA, read


def load_config():
    return yaml.safe_load(read(DATA / "soar.yaml"))


def decide(alert, config):
    if alert["src_ip"] in config["whitelist"]:
        return "ignorer", "adresse en liste blanche"
    if alert["severity"] not in config["block_severities"]:
        return "ignorer", "sévérité insuffisante"
    return "bloquer", "sévérité élevée"


def handle(device, alert, config, log_path):
    decision, reason = decide(alert, config)
    if decision == "bloquer":
        payload = {
            "list": "blocked",
            "address": alert["src_ip"],
            "timeout": config["block_duration"],
            "comment": alert["signature"],
        }
        _, created = device.ensure("ip/firewall/address-list", payload, ["list", "address"])
        reason = "blocage créé" if created else "déjà bloquée"
    entry = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "alert": alert, "decision": decision, "reason": reason}
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return decision, reason


ALERTS = [
    {"src_ip": "203.0.113.7", "signature": "SSH brute force", "severity": "high"},
    {"src_ip": "10.0.20.53", "signature": "Scan de ports", "severity": "critical"},
    {"src_ip": "198.51.100.4", "signature": "Ping sweep", "severity": "low"},
    {"src_ip": "203.0.113.7", "signature": "SSH brute force", "severity": "high"},
]
