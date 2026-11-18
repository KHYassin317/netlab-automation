from netlab import compliance, firewall, iac, k8s, rest, soar


def test_render_contains_desired_state():
    hosts = iac.inventory()
    text = iac.render("r1", hosts["r1"])
    assert "/ip address add address=192.168.10.1/24 interface=ether1" in text
    assert "/ip route add dst-address=0.0.0.0/0 gateway=192.168.10.254" in text


def test_drift_apply_idempotent(lab):
    device = rest.Device()
    host = iac.inventory()["r1"]
    before = iac.diff(device, host)
    assert before["missing"] and before["extra"]
    assert iac.apply(device, host, prune=True)
    assert iac.apply(device, host, prune=True) == []
    after = iac.diff(device, host)
    assert not after["missing"] and not after["extra"]


def test_prune_is_opt_in(lab):
    device = rest.Device()
    host = iac.inventory()["r1"]
    iac.apply(device, host)
    assert iac.diff(device, host)["extra"]


def test_firewall_pipeline_ok():
    report, ok = firewall.pipeline()
    assert ok and [r[1] for r in report] == ["OK", "OK", "OK"]


def test_firewall_rejects_any_any():
    report, ok = firewall.pipeline(rules_file="rules_bad.yaml")
    assert not ok
    assert report[-1][0] == "validation" and "any-any" in report[-1][2]


def test_firewall_lint():
    assert firewall.lint([{"name": "x", "src": "999.1.1.1", "dst": "any", "proto": "tcp", "port": 80, "action": "accept"}])
    assert firewall.lint([{"name": "y", "action": "accept"}])


def test_regression_detects_opening():
    rules = firewall.load("rules.yaml")["rules"]
    flows = firewall.load("flows.yaml")["flows"]
    assert firewall.regression(rules, flows) == []
    opened = rules[:-1] + [{**rules[-1], "action": "accept"}]
    assert firewall.regression(opened, flows)


def test_firewall_deploy_idempotent(lab):
    device = rest.Device()
    rules = firewall.load("rules.yaml")["rules"]
    assert {r[1] for r in firewall.deploy(device, rules)} == {"créée"}
    assert {r[1] for r in firewall.deploy(device, rules)} == {"déjà présente"}


def test_soar_playbook(lab, tmp_path):
    device = rest.Device()
    config = soar.load_config()
    log = tmp_path / "soar.log"
    results = [soar.handle(device, alert, config, log) for alert in soar.ALERTS]
    assert [r[0] for r in results] == ["bloquer", "ignorer", "ignorer", "bloquer"]
    assert results[3][1] == "déjà bloquée"
    assert len(device.list("ip/firewall/address-list")) == 1
    assert len(log.read_text(encoding="utf-8").splitlines()) == 4


def test_k8s_policies_ok():
    assert k8s.check(k8s.load_policies()) == []


def test_k8s_detects_problems():
    allow_all = {
        "kind": "NetworkPolicy",
        "metadata": {"name": "open", "namespace": "prod"},
        "spec": {"podSelector": {}, "policyTypes": ["Ingress"], "ingress": [{}]},
    }
    by_ip = {
        "kind": "NetworkPolicy",
        "metadata": {"name": "by-ip", "namespace": "prod"},
        "spec": {"podSelector": {}, "ingress": [{"from": [{"ipBlock": {"cidr": "10.0.0.0/8"}}]}]},
    }
    problems = k8s.check([allow_all, by_ip])
    assert any("default-deny" in p for p in problems)
    assert any("règle vide" in p for p in problems)
    assert any("ipBlock" in p for p in problems)


def test_compliance_audit_and_remediation(lab):
    device = rest.Device()
    before = {r[0]: r[3] for r in compliance.audit(device)}
    assert before["C1"] == "NON CONFORME" and before["C2"] == "OK"
    assert compliance.remediate(device) == ["telnet", "www"]
    after = {r[0]: r[3] for r in compliance.audit(device)}
    assert after["C1"] == "OK" and after["C3"] == "OK" and after["C4"] == "NON CONFORME"
    assert "| C1 |" in compliance.report("lab", compliance.audit(device))
