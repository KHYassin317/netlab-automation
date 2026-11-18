import argparse
import os
import sys
import tempfile
from pathlib import Path

from . import compliance, firewall, iac, k8s, mock, netconf, restconf, rest, soar, ubus
from .config import ROOT, env


def table(headers, rows):
    rows = [[str(c) for c in row] for row in rows]
    widths = [max([len(h)] + [len(r[i]) for r in rows]) for i, h in enumerate(headers)]
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(line)
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(c.ljust(w) for c, w in zip(row, widths)))
    print()


def title(text):
    print(f"\n=== {text} ===\n")


def m2_crud(args):
    table(["Verbe", "Ressource", "Résultat"], rest.crud_demo(rest.Device()))


def m2_routes(args):
    table(["Destination", "Passerelle", "État"], rest.ensure_routes(rest.Device()))


def m2_ubus(args):
    table(["Appel ubus", "Résultat"], ubus.demo())


def m3_restconf(args):
    table(["Verbe", "Ressource", "Résultat"], restconf.demo())


def m3_netconf(args):
    print(netconf.get_config())
    print(netconf.edit_config("GigabitEthernet2", True))
    print()
    table(["Opération", "Résultat"], netconf.demo())


def m4_render(args):
    for name, host in iac.inventory().items():
        print(f"--- {name} ---")
        print(iac.render(name, host))


def m4_drift(args):
    rows = []
    for name, changes in iac.run_parallel(lambda d, h: iac.diff(d, h), iac.inventory()).items():
        rows += [(name, "manquant", path, item) for path, item in changes["missing"]]
        rows += [(name, "en trop", path, item) for path, item in changes["extra"]]
    table(["Hôte", "Écart", "Ressource", "Élément"], rows or [("-", "aucune dérive", "-", "-")])


def m4_apply(args):
    results = iac.run_parallel(lambda d, h: iac.apply(d, h, prune=args.prune), iac.inventory())
    rows = [(name, *action) for name, actions in results.items() for action in actions]
    table(["Hôte", "Action", "Ressource", "Clé"], rows or [("-", "rien à faire", "-", "-")])


def m5_pipeline(args):
    device = rest.Device() if args.deploy else None
    report, ok = firewall.pipeline(device, args.file)
    table(["Étape", "Résultat", "Détail"], report)
    sys.exit(0 if ok else 1)


def m5_soar(args):
    config = soar.load_config()
    device = rest.Device()
    log = env("SOAR_LOG", "soar.log")
    rows = [(a["src_ip"], a["signature"], a["severity"], *soar.handle(device, a, config, log)) for a in soar.ALERTS]
    table(["IP source", "Alerte", "Sévérité", "Décision", "Raison"], rows)


def m5_k8s(args):
    problems = k8s.check(k8s.load_policies())
    table(["Contrôle NetworkPolicy"], [(p,) for p in problems] or [("OK : default-deny présent, sélecteurs par labels",)])
    sys.exit(1 if problems else 0)


def m5_compliance(args):
    device = rest.Device()
    results = compliance.audit(device)
    if args.fix:
        table(["Remédiation"], [(f"service {s} désactivé",) for s in compliance.remediate(device)] or [("rien à corriger",)])
        results = compliance.audit(device)
    table(["ID", "Contrôle", "Criticité", "Résultat"], results)
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "compliance.md").write_text(compliance.report(device.host, results), encoding="utf-8")
    sys.exit(1 if compliance.blocking(results) else 0)


def demo(args):
    ports = (8080, 8081)
    for port in ports:
        mock.start(port)
    os.environ.update(
        DEVICE_SCHEME="http",
        DEVICE_HOST=f"127.0.0.1:{ports[0]}",
        DEVICE_USER="api-user",
        DEVICE_PASSWORD="lab-pass",
        DEVICE_CREATE_VERB="POST",
        UBUS_USER="root",
        UBUS_PASSWORD="openwrt",
        SOAR_LOG=str(Path(tempfile.gettempdir()) / "netlab-soar.log"),
    )
    steps = [
        ("Module 2 - REST : CRUD sur /ip/address", m2_crud, {}),
        ("Module 2 - REST : routes statiques idempotentes (1er passage)", m2_routes, {}),
        ("Module 2 - REST : relance (aucun doublon)", m2_routes, {}),
        ("Module 2 - JSON-RPC : ubus (OpenWrt)", m2_ubus, {}),
        ("Module 3 - RESTCONF : ietf-interfaces", m3_restconf, {}),
        ("Module 3 - NETCONF : candidate, running, lock", m3_netconf, {}),
        ("Module 4 - IaC : configuration générée (Jinja2)", m4_render, {}),
        ("Module 4 - IaC : dérive détectée (parallèle)", m4_drift, {}),
        ("Module 4 - IaC : convergence vers l'état désiré", m4_apply, {"prune": True}),
        ("Module 4 - IaC : relance (idempotent)", m4_drift, {}),
        ("Module 5 - Firewall-as-Code : lint, validation, tests, déploiement", m5_pipeline, {"deploy": True, "file": "rules.yaml"}),
        ("Module 5 - Firewall-as-Code : règles invalides refusées", m5_pipeline, {"deploy": False, "file": "rules_bad.yaml"}),
        ("Module 5 - SOAR : playbook de blocage", m5_soar, {}),
        ("Module 5 - Kubernetes : NetworkPolicy", m5_k8s, {}),
        ("Module 5 - Compliance-as-Code : audit", m5_compliance, {"fix": False}),
        ("Module 5 - Compliance-as-Code : remédiation puis audit", m5_compliance, {"fix": True}),
    ]
    for label, step, options in steps:
        title(label)
        try:
            step(argparse.Namespace(**options))
        except SystemExit as stop:
            if stop.code not in (0, None):
                print(f"(code de sortie {stop.code} : échec attendu pour ce scénario)\n")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="netlab", description="Mini projet NetDevOps : modules 1 à 5")
    commands = parser.add_subparsers(dest="command", required=True)

    def add(name, function, help_text):
        sub = commands.add_parser(name, help=help_text)
        sub.set_defaults(function=function)
        return sub

    add("m2-crud", m2_crud, "CRUD REST sur /ip/address")
    add("m2-routes", m2_routes, "routes statiques idempotentes")
    add("m2-ubus", m2_ubus, "JSON-RPC ubus (OpenWrt)")
    add("m3-restconf", m3_restconf, "RESTCONF ietf-interfaces")
    add("m3-netconf", m3_netconf, "NETCONF simulé : candidate, running, lock")
    add("m4-render", m4_render, "génération Jinja2 depuis l'inventaire")
    add("m4-drift", m4_drift, "détection de dérive")
    add("m4-apply", m4_apply, "convergence vers l'état désiré").add_argument("--prune", action="store_true")
    pipe = add("m5-pipeline", m5_pipeline, "pipeline Firewall-as-Code")
    pipe.add_argument("--file", default="rules.yaml")
    pipe.add_argument("--deploy", action="store_true")
    add("m5-soar", m5_soar, "playbook SOAR")
    add("m5-k8s", m5_k8s, "contrôle des NetworkPolicy")
    add("m5-compliance", m5_compliance, "audit Compliance-as-Code").add_argument("--fix", action="store_true")
    add("demo", demo, "démonstration complète sur le lab simulé")

    args = parser.parse_args()
    args.function(args)
