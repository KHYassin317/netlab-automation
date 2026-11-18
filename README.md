# netlab-automation

Mini projet NetDevOps qui couvre les 5 modules du cours : Git/GitHub, API REST, YANG/SDN, NetDevOps, NetSecDevOps.
Tout tourne sans VM grâce à un lab simulé (`netlab/mock.py`) qui imite RouterOS (REST), OpenWrt (ubus JSON-RPC) et un équipement RESTCONF.

## Installation

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
```

Si `Scripts` n'existe pas, utiliser `source .venv/bin/activate`.

## Démonstration complète

```bash
python -m netlab demo
python -m pytest -q
```

## Modules couverts

| Module | Notions | Fichiers |
|---|---|---|
| 1 | Git, `.gitignore` (`.env`), CODEOWNERS, modèle de PR, CI | `.github/`, `.gitignore`, `bootstrap_repo.sh` |
| 2 | REST (CRUD, session, timeout, idempotence), secrets en `.env`, JSON-RPC | `netlab/rest.py`, `netlab/ubus.py` |
| 3 | YANG, RESTCONF, NETCONF (candidate, running, lock) | `data/yang/`, `netlab/restconf.py`, `netlab/netconf.py` |
| 4 | IaC déclaratif, inventaire, Jinja2, dérive, exécution parallèle | `netlab/iac.py`, `data/inventory.yaml`, `data/templates/` |
| 5 | Firewall-as-Code, shift-left, SOAR, NetworkPolicy, Compliance-as-Code | `netlab/firewall.py`, `netlab/soar.py`, `netlab/k8s.py`, `netlab/compliance.py` |

## Commandes

Pour les commandes `m*`, démarrer d'abord le lab dans un terminal : `python -m netlab.mock`

| Commande | Rôle | Résultat |
|---|---|---|
| `python -m netlab.mock` | Lance 2 routeurs simulés (ports 8080 et 8081) | Lab accessible en local |
| `python -m netlab m2-crud` | POST, GET, PATCH, DELETE sur `/ip/address` | Tableau des 4 opérations |
| `python -m netlab m2-routes` | Crée les routes statiques manquantes | `créée` puis `déjà présente` à la relance |
| `python -m netlab m2-ubus` | Login ubus puis changement d'IP via uci | IP `lan` modifiée |
| `python -m netlab m3-restconf` | Lit et modifie `ietf-interfaces` | `enabled` basculé |
| `python -m netlab m3-netconf` | Rôle de `candidate`, `running`, `lock` | `running` change après `commit` |
| `python -m netlab m4-render` | Génère les configs depuis l'inventaire | Configs MikroTik par hôte |
| `python -m netlab m4-drift` | Compare état désiré et état réel | Liste des écarts |
| `python -m netlab m4-apply` | Crée ce qui manque (`--prune` supprime l'excédent) | Convergence, puis aucune action à la relance |
| `python -m netlab m5-pipeline` | lint, validation, tests de flux | `OK` ou `ÉCHEC` (code de sortie) |
| `python -m netlab m5-pipeline --file rules_bad.yaml` | Teste des règles invalides | Refus : règle any-any |
| `python -m netlab m5-pipeline --deploy` | Déploie après validation | Règles dans `ip/firewall/filter` |
| `python -m netlab m5-soar` | Playbook : bloque, ignore, journalise | `soar.log` + blocage temporaire |
| `python -m netlab m5-k8s` | Vérifie default-deny et labels | `OK` ou liste de problèmes |
| `python -m netlab m5-compliance` | Audit de conformité (`--fix` remédie) | `reports/compliance.md` |

## Utiliser de vrais équipements

Modifier `.env` (`DEVICE_SCHEME=https`, `DEVICE_HOST=192.168.56.10`, vrais identifiants) et `data/inventory.yaml`.
Si RouterOS refuse le `POST` de création, mettre `DEVICE_CREATE_VERB=PUT`.
Ne pas utiliser `--prune` sur un vrai équipement sans relire `m4-drift` : une adresse de gestion pourrait être supprimée.

## Git

`bootstrap_repo.sh` crée le dépôt avec un historique par module, le tag `v1.0.0`, puis pousse vers GitHub.
`.github/CODEOWNERS` pointe vers le propriétaire du dépôt : le remplacer par le pseudo du relecteur pour le TP 4.
