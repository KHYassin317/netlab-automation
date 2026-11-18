import yaml

from .config import DATA, read


def load_policies():
    docs = []
    for path in sorted((DATA / "k8s").glob("*.yaml")):
        docs += [d for d in yaml.safe_load_all(read(path)) if d]
    return docs


def namespace(policy):
    return policy["metadata"].get("namespace", "default")


def is_default_deny(policy):
    spec = policy["spec"]
    return (
        spec.get("podSelector") == {}
        and set(spec.get("policyTypes", [])) == {"Ingress", "Egress"}
        and not spec.get("ingress")
        and not spec.get("egress")
    )


def check(docs):
    problems = []
    policies = [d for d in docs if d.get("kind") == "NetworkPolicy"]
    for ns in sorted({namespace(p) for p in policies}):
        if not any(is_default_deny(p) for p in policies if namespace(p) == ns):
            problems.append(f"namespace {ns} : pas de politique default-deny")
    for policy in policies:
        name = policy["metadata"]["name"]
        rules = (policy["spec"].get("ingress") or []) + (policy["spec"].get("egress") or [])
        for rule in rules:
            if not rule:
                problems.append(f"{name} : règle vide (autorise tout)")
            for peer in (rule.get("from") or []) + (rule.get("to") or []):
                if "ipBlock" in peer:
                    problems.append(f"{name} : ipBlock utilisé, préférer les labels")
    return problems
