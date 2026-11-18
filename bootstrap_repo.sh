#!/bin/bash
set -e
cd "$(dirname "$0")"

GH_USER="${1:-KHYassin317}"
EMAIL="${2:-khalifayassin88@gmail.com}"
REMOTE="${3:-git@github.com:$GH_USER/netlab-automation.git}"

git init -q
git branch -M main
git config user.name "Khalifa Yassin"
git config user.email "$EMAIL"

commit() {
  message="$1"
  shift
  git add "$@"
  git commit -q -m "$message"
}

commit "chore: base du projet et lab simulé" README.md bootstrap_repo.sh .gitignore .env.example requirements.txt netlab/__init__.py netlab/__main__.py netlab/config.py netlab/mock.py
commit "chore(git): CODEOWNERS et modèle de pull request" .github/CODEOWNERS .github/pull_request_template.md
commit "feat(m2): client REST idempotent et JSON-RPC ubus" netlab/rest.py netlab/ubus.py
commit "feat(m3): RESTCONF, NETCONF simulé et modèle YANG" netlab/restconf.py netlab/netconf.py data/yang
commit "feat(m4): IaC déclaratif, inventaire et templates Jinja2" netlab/iac.py data/inventory.yaml data/templates
commit "feat(m5): Firewall-as-Code, SOAR, NetworkPolicy et compliance" netlab/firewall.py netlab/soar.py netlab/k8s.py netlab/compliance.py data/firewall data/soar.yaml data/k8s
commit "feat(cli): commandes netlab et démonstration" netlab/cli.py
commit "test: suite pytest des modules 2 à 5" tests
commit "ci: workflow GitHub Actions" .github/workflows/ci.yml

git tag -a v1.0.0 -m "Première version du mini projet"
git log --oneline --graph

git remote add origin "$REMOTE"
git push -u origin main --tags
