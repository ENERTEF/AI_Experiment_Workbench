# AI Experiment Workbench — Docker Compose

A Docker Compose port of the [ENERTEF AI Experiment Workbench](https://github.com/ENERTEF/AI_Experiment_Workbench)
(originally a Helm chart for Kubernetes). It provides a multi-user ML platform:

- **JupyterHub**: per-user JupyterLab containers with ML packages, MLflow and TensorBoard launchers
- **Keycloak**: login and roles (`mlflow-user` / `mlflow-admin`)
- **MLflow**: experiment tracking, with one isolated workspace per user
- **Postgres + MinIO**: MLflow metadata and artifact storage
- **Flower** (optional): federated learning (SuperLink, SuperNode, per-user CLI sidecar)

Only one port is published: the `proxy` service. All services talk to each other by service name on the internal `workbench` network.

---

## Architecture

```
 Browser ──► proxy (Caddy, :PROXY_PORT)
               ├── /auth/*  ──► keycloak:8080
               └── /*       ──► jupyterhub:8000
                                   │  login via Keycloak (OIDC)
                                   │  provisions MLflow user + workspace
                                   └─► spawns jupyter-<user> containers (Docker socket)
                                          │
                                          ├─► mlflow-svc:5000 ──► postgres:5432 (metadata)
                                          │                   └─► minio:9000    (artifacts)
                                          └─► flower-sidecar-<user> ──► flower-superlink:9093
                                                                         ▲
                                              flower-supernode ──────────┘ :9092 (TLS)
```

| Service | Purpose | Internal address |
|---|---|---|
| `proxy` | Single entry point | published on `PROXY_PORT` |
| `jupyterhub` | Hub + DockerSpawner | `jupyterhub:8000` |
| `keycloak` | Identity provider (realm `mlflow-workbench`) | `keycloak:8080/auth` |
| `mlflow-svc` | Tracking server with basic auth | `mlflow-svc:5000` |
| `postgres` | DBs `mlflow` and `keycloak` | `postgres:5432` |
| `minio` / `minio-init` | S3 artifact store / bucket creation | `minio:9000` |
| `flower-*` | Federated learning (profile `flower`) | `flower-superlink:9091-9093` |

---

## Folder layout

```
docker/
├── docker-compose.yml
├── .env.example                 # copy to .env
├── proxy/Caddyfile
├── postgres/init/01-keycloak-db.sql
├── mlflow/auth.ini.example      # copy to auth.ini
├── keycloak/import/mlflow-workbench-realm.json
├── jupyterhub/
│   ├── jupyterhub_config.py
│   └── jupyter_server_config.py
├── flower/register/{register.py,config.toml}
├── certs/                       # generated, not in git
└── data/                        # runtime data, not in git
```

Default notebooks are mounted from `../mlflow-workbench/files`.

---

## Prerequisites

- Linux host with **Docker Engine** and **Docker Compose v2** (`docker compose version`)
- Your user in the `docker` group
- Roughly 20 GB free disk space (the notebook image is large)
- One free TCP port for the proxy (default `8888`)

---

## Installation

All commands are run from the `docker/` folder.

### 1. Clone

```bash
git clone <this-repo-url>
cd <repo>/docker
```

### 2. Configure `.env`

```bash
cp .env.example .env
```

Generate the secrets:

```bash
openssl rand -hex 32     # JUPYTERHUB_CRYPT_KEY
openssl rand -hex 16     # KC_JHUB_CLIENT_SECRET
openssl rand -base64 32  # MLFLOW_FLASK_SECRET_KEY
openssl rand -hex 24     # passwords (hex avoids URL-escaping problems)
```

Set at least:

| Variable | Example | Notes |
|---|---|---|
| `PROXY_PORT` | `8888` | must be free on the host |
| `PUBLIC_URL` | `http://my-host.example.org:8888` | **no slash before the port** |
| `JHUB_URL` | same as `PUBLIC_URL` | |
| `EXPOSE_HOSTNAME` | `my-host.example.org` | hostname only |
| `HOST_PROJECT_DIR` | `/home/me/<repo>/docker` | output of `pwd`; used for user bind mounts |
| `POSTGRES_PASSWORD` | generated | set **before** first start |
| `MINIO_PASSWORD` | generated | |
| `MLFLOW_ADMIN_PASSWORD` | generated | must match `auth.ini` |
| `MLFLOW_FED_PASSWORD` | generated | Flower only |
| `KEYCLOAK_ADMIN_USERNAME` / `_PASSWORD` | `admin` / generated | Keycloak admin console |
| `KC_JHUB_CLIENT_SECRET` | generated | |
| `JUPYTERHUB_CRYPT_KEY` | generated (64 hex chars) | |
| `COMPOSE_PROFILES` | `flower` or empty | empty = no Flower |

Check that no placeholder is left:

```bash
grep changeme .env
```

Keep comments on their own lines in `.env`, never after a value.

### 3. Configure MLflow auth

```bash
cp mlflow/auth.ini.example mlflow/auth.ini
```

Edit it so that it matches `.env`:

```ini
[mlflow]
default_permission = NO_PERMISSIONS
database_uri = postgresql://<POSTGRES_USER>:<POSTGRES_PASSWORD>@postgres:5432/<POSTGRES_DB>
admin_username = <MLFLOW_ADMIN_USERNAME>
admin_password = <MLFLOW_ADMIN_PASSWORD>
authorization_function = mlflow.server.auth:authenticate_request_basic_auth
```

### 4. Data folders

```bash
mkdir -p data/postgres data/minio data/jupyterhub data/jupyter-users data/supernode-keys
sudo chown -R 1001:1001 data/minio      # MinIO runs as UID 1001
```

Config files must exist **before** the first start. If a bind-mounted file is missing, Docker creates an empty directory in its place.

### 5. Flower TLS certificates (only if Flower is enabled)

```bash
mkdir -p certs && cd certs
openssl req -x509 -newkey rsa:4096 -nodes -keyout ca.key -out ca.crt -days 3650 -subj "/CN=workbench-flower-ca"
openssl req -newkey rsa:4096 -nodes -keyout tls.key -out tls.csr -subj "/CN=flower-superlink"
echo "subjectAltName=DNS:flower-superlink,DNS:localhost" > san.ext
openssl x509 -req -in tls.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out tls.crt -days 825 -extfile san.ext
chmod 644 ca.crt tls.crt tls.key
cd ..
```

### 6. Open the port

```bash
sudo ufw allow <PROXY_PORT>/tcp
```

Also allow it in any cloud or institutional firewall in front of the host.

### 7. Start

```bash
docker compose pull
docker pull registry.git.nrw/rwth-acs/public/ai-workbench/notebook:latest
docker pull registry.git.nrw/rwth-acs/public/ai-workbench/flower-sidecar:latest   # if Flower
docker compose up -d --build
docker compose ps -a
```

All services should be `Up`. The one-shot services `minio-init`, `flower-fed-init` and `flower-supernode-register` should be `Exited (0)`. Keycloak needs about a minute on the first start.

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:<PROXY_PORT>/hub/login                    # 200
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:<PROXY_PORT>/auth/realms/mlflow-workbench # 200
```

### 8. Allow the Keycloak admin console over HTTP (one time)

The workbench realm already allows HTTP (`sslRequired: none` in the realm file). The `master` realm, which serves the admin console, does not:

```bash
KCADM="docker compose exec -T keycloak /opt/keycloak/bin/kcadm.sh"
$KCADM config credentials --server http://localhost:8080/auth --realm master \
  --user "$(grep ^KEYCLOAK_ADMIN_USERNAME .env | cut -d= -f2)" \
  --password "$(grep ^KEYCLOAK_ADMIN_PASSWORD .env | cut -d= -f2)"
$KCADM update realms/master -s sslRequired=NONE
```

This persists because Keycloak stores its data in Postgres.

### 9. Secure the demo accounts

The realm ships with two demo users. Change their passwords or delete them in the admin console
(`<PUBLIC_URL>/auth/admin/` → realm **mlflow-workbench** → Users).

---

## Usage

| What | URL | Login |
|---|---|---|
| JupyterHub | `<PUBLIC_URL>` | Keycloak users of realm `mlflow-workbench` |
| Keycloak admin | `<PUBLIC_URL>/auth/admin/` | `KEYCLOAK_ADMIN_*` from `.env` (realm `master`) |
| MLflow UI | "MLflow UI" launcher inside JupyterLab | automatic, per user |

Demo users: `standard-user` / `user123` (role `mlflow-user`) and `admin-user` / `admin123` (role `mlflow-admin`).

### Adding a user

In the admin console, realm **mlflow-workbench**:

1. **Users → Add user.** Set a username and turn on *Email verified*.
2. **Credentials → Set password.** Turn *Temporary* off.
3. **Role mapping → Assign role → Filter by clients.** Pick `jhub-mlfw mlflow-user` or `mlflow-admin`.

A user without one of these roles gets a 403 from JupyterHub.

### What happens at login

1. JupyterHub authenticates the user with Keycloak and reads the `roles` claim.
2. It creates or updates the user's MLflow account with a random session password. Non-admins also get a workspace `ws-<user>`.
3. It prepares `data/jupyter-users/<user>/`, copies in the default notebooks and sets ownership to `1000:100`.
4. It starts `jupyter-<user>` with `MLFLOW_TRACKING_*` already set. If Flower is enabled, it also starts `flower-sidecar-<user>`.

### Federated learning (Flower)

Enable it with `COMPOSE_PROFILES=flower` in `.env`. Then, in a JupyterLab terminal:

```bash
mkdir -p ~/user && cp ~/exports.py ~/user/
cd ~/user && z2jh_flwr run --stream
```

The project must live in `~/user` and contain an `exports.py` with `train`, `evaluate`, `DEPENDENCIES` and `CAPABILITIES`. If `CAPABILITIES` asks for something no SuperNode offers, no node is scheduled. Use `{}` to accept any node.

`flower-fed-init` prints the federated experiment ID on first run. It must match `FEDERATED_EXPERIMENT_ID` in `.env`.

---

## Operations

```bash
docker compose ps -a                         # status
docker compose logs -f <service>             # logs
docker compose up -d --force-recreate <svc>  # apply .env / config changes
docker compose down                          # stop (data is kept)
```

Notebook and sidecar containers are created by the hub, not by Compose. Stop them with:

```bash
docker rm -f $(docker ps -aq --filter "name=jupyter-" --filter "name=flower-sidecar-")
```

### Update

```bash
git pull
docker compose pull
docker compose up -d --build
```

### Backup

All state lives in `data/` and in Postgres:

```bash
docker compose exec -T postgres pg_dumpall -U "$(grep ^POSTGRES_USER .env | cut -d= -f2)" > backup-$(date +%F).sql
sudo tar czf data-$(date +%F).tgz data/
```

### Reset Keycloak to the realm file

The realm file is imported only once, when the realm doesn't exist yet. To re-import it:

```bash
docker compose exec postgres psql -U "$(grep ^POSTGRES_USER .env | cut -d= -f2)" -d postgres \
  -c "DROP DATABASE keycloak;" -c "CREATE DATABASE keycloak;"
docker compose up -d --force-recreate keycloak
```

Then repeat step 8.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `container name ... already in use` | Another stack on the host uses that name. This compose file sets no fixed names; containers are prefixed `workbench-`. |
| Port conflict on start | Choose another `PROXY_PORT` (check with `sudo ss -ltnp`). |
| 404 on "Sign in with keycloak" | Bad `PUBLIC_URL`, e.g. `http://host/:8888`. It must be `http://host:8888`. Recreate `keycloak` and `jupyterhub` after fixing. |
| 502 on the Keycloak page | Keycloak is still starting (about 1 min) or failing: `docker compose logs keycloak`. |
| "HTTPS required" | Run step 8 (admin console), or check `sslRequired` on the workbench realm. |
| "Invalid redirect uri" | The client's redirect URI must be `<PUBLIC_URL>/*`: Clients → `jhub-mlfw` → Valid redirect URIs. |
| JupyterHub exits: "Encryption keys must be 32 bytes" | `JUPYTERHUB_CRYPT_KEY` must be 64 hex characters. |
| MLflow `KeyError: 'mlflow'` | `mlflow/auth.ini` is missing or empty, or Docker created it as a directory. |
| MLflow 401 in browser | Use a private window. The credentials come from `auth.ini`. |
| Notebook spawn timeout | The first pull of the notebook image is slow. Pre-pull it, then click "Start My Server" again. |
| MinIO permission denied | `sudo chown -R 1001:1001 data/minio` |

---

## Moving to HTTPS

1. Get a dedicated hostname, e.g. `workbench.example.org`, pointing to the host.
2. Put a TLS-terminating reverse proxy in front, such as Nginx Proxy Manager on the `workbench` network: `/` → `jupyterhub:8000`, `/auth` → `keycloak:8080`, with websockets enabled.
3. Remove the `proxy` service and close `PROXY_PORT`.
4. Set `PUBLIC_URL=https://workbench.example.org` (and `JHUB_URL`, `EXPOSE_HOSTNAME`), then recreate `keycloak`, `jupyterhub` and `mlflow-svc`.
5. In Keycloak, update the redirect URI and set `sslRequired` back to `external` on both realms.

---

## Security notes

- The hub mounts `/var/run/docker.sock`. Hub admins effectively control the host, so only give admin roles to trusted users.
- Plain HTTP sends passwords unencrypted. Use it for testing only.
- Never commit `.env`, `mlflow/auth.ini`, `certs/` or `data/` (see `.gitignore`).

---

## Credits

Based on [ENERTEF/AI_Experiment_Workbench](https://github.com/ENERTEF/AI_Experiment_Workbench) (Apache-2.0).
Container images by RWTH ACS (`registry.git.nrw/rwth-acs/public/ai-workbench/*`), Flower, Keycloak, MLflow and CloudPirates.
