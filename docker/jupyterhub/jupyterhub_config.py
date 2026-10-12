import os, json, base64, secrets, shutil, requests

c = get_config()

# ================= Hub basics =================
c.JupyterHub.bind_url = "http://0.0.0.0:8000"
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_connect_ip = "jupyterhub"          # notebooks reach the hub by container name
c.JupyterHub.db_url = "sqlite:////srv/jupyterhub/data/jupyterhub.sqlite"   # was: sqlite-pvc
c.JupyterHub.cookie_secret_file = "/srv/jupyterhub/data/jupyterhub_cookie_secret"
c.JupyterHub.admin_access = True

# ================= Auth (was: auth_config.py) =================
KC_PUBLIC = os.environ["KC_PUBLIC_REALM_URL"]      # what the browser uses
KC_INTERNAL = os.environ["KC_INTERNAL_REALM_URL"]  # what the hub container uses

c.JupyterHub.authenticator_class = "generic-oauth"
c.GenericOAuthenticator.manage_groups = True
c.GenericOAuthenticator.enable_auth_state = True
c.GenericOAuthenticator.login_service = "keycloak"
c.GenericOAuthenticator.username_claim = "preferred_username"
c.GenericOAuthenticator.scope = ["openid"]
c.GenericOAuthenticator.userdata_params = {"state": "state"}
c.GenericOAuthenticator.auth_state_groups_key = "oauth_user.roles"
c.GenericOAuthenticator.client_id = os.environ["KC_CLIENT_ID"]
c.GenericOAuthenticator.client_secret = os.environ["KC_CLIENT_SECRET"]
c.GenericOAuthenticator.authorize_url = f"{KC_PUBLIC}/protocol/openid-connect/auth"
c.GenericOAuthenticator.token_url = f"{KC_INTERNAL}/protocol/openid-connect/token"
c.GenericOAuthenticator.userdata_url = f"{KC_INTERNAL}/protocol/openid-connect/userinfo"
c.GenericOAuthenticator.oauth_callback_url = f"{os.environ['JHUB_URL']}/hub/oauth_callback"
c.GenericOAuthenticator.allowed_groups = ["mlflow-user"]
c.GenericOAuthenticator.admin_groups = ["mlflow-admin"]

# ================= Spawner (was: KubeSpawner via z2jh singleuser values) =================
HOST_DIR = os.environ["HOST_PROJECT_DIR"]   # host path, because the Docker daemon resolves bind mounts

c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"
c.DockerSpawner.image = os.environ["NOTEBOOK_IMAGE"]
c.DockerSpawner.pull_policy = "always"                 # was: pullPolicy: Always
c.DockerSpawner.network_name = "workbench"
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.remove = True                          # containers are disposable, home persists
c.DockerSpawner.name_template = "jupyter-{username}"   # was: podNameTemplate pod-{username}
c.DockerSpawner.cmd = ["jupyterhub-singleuser"]
c.DockerSpawner.extra_create_kwargs = {"user": "1000:100"}   # was: uid 1000 / fsGid 100
c.DockerSpawner.notebook_dir = "/home/jovyan"
c.DockerSpawner.volumes = {
    # was: dynamic PVC claim-{username}
    f"{HOST_DIR}/data/jupyter-users/{{username}}": "/home/jovyan",
    # was: ConfigMap jhub-extra-config -> jupyter_server_config.py
    f"{HOST_DIR}/jupyterhub/jupyter_server_config.py": {
        "bind": "/etc/jupyter/jupyter_server_config.py", "mode": "ro"},
}
c.Spawner.default_url = "/lab/tree/mlflow_tensorboard_examples.ipynb"
c.Spawner.http_timeout = 60
c.Spawner.start_timeout = 300   # first spawn pulls the notebook image

# ================= Home prep (was: init container "copy-defaults") =================
def prepare_home(spawner):
    home = f"/srv/users/{spawner.escaped_name}"
    os.makedirs(home, exist_ok=True)
    src = "/srv/default-files"
    if os.path.isdir(src) and os.listdir(src):
        shutil.copytree(src, home, dirs_exist_ok=True)   # same as cp -rfL: overwrites defaults
        spawner.log.info("Copied default files to user home directory.")
    for root, dirs, files in os.walk(home):
        os.chown(root, 1000, 100)
        for f in files:
            os.chown(os.path.join(root, f), 1000, 100)

# c.Spawner.pre_spawn_hook = prepare_home
# ================= Flower sidecar (was: flower_hook + extra_containers) =================
import docker

FLOWER_SIDECAR = os.environ.get("FLOWER_SIDECAR_ENABLED", "false").lower() == "true"

def sidecar_name(spawner):
    return f"flower-sidecar-{spawner.escaped_name}"

def start_flower_sidecar(spawner):
    client = docker.from_env()
    user = spawner.escaped_name
    for d in ("user", ".pipes"):
        p = f"/srv/users/{user}/{d}"
        os.makedirs(p, exist_ok=True)
        os.chown(p, 1000, 100)
    try:
        client.containers.get(sidecar_name(spawner)).remove(force=True)
    except docker.errors.NotFound:
        pass
    env = spawner.environment
    client.containers.run(
        os.environ["FLOWER_SIDECAR_IMAGE"],
        name=sidecar_name(spawner),
        detach=True,
        user="0:100",                    # was: runAsGroup 100; pipes get group 100 so jovyan can use them
        network="workbench",
        volumes={
            f"{HOST_DIR}/data/jupyter-users/{user}/user":   {"bind": "/app/flower/user", "mode": "rw"},
            f"{HOST_DIR}/data/jupyter-users/{user}/.pipes": {"bind": "/app/.pipes", "mode": "rw"},
            f"{HOST_DIR}/certs/ca.crt":                     {"bind": "/app/ca.crt", "mode": "ro"},
        },
        environment={
            "ROOT_CERT_PATH": "/app/ca.crt",
            "SUPERLINK_CONTROL": os.environ["SUPERLINK_CONTROL"],
            "PYTHONUNBUFFERED": "1",
            "MLFLOW_EXTERNAL_TRACKING_URI": env.get("MLFLOW_EXTERNAL_TRACKING_URI", ""),
            "MLFLOW_TRACKING_USERNAME": env.get("MLFLOW_TRACKING_USERNAME", ""),
            "MLFLOW_TRACKING_PASSWORD": env.get("MLFLOW_TRACKING_PASSWORD", ""),
            "MLFLOW_WORKSPACE": env.get("MLFLOW_WORKSPACE", "default"),
        },
    )
    spawner.log.info(f"Flower: started {sidecar_name(spawner)}")

def stop_flower_sidecar(spawner):
    try:
        docker.from_env().containers.get(sidecar_name(spawner)).remove(force=True)
    except docker.errors.NotFound:
        pass

def pre_spawn(spawner):
    prepare_home(spawner)
    if FLOWER_SIDECAR:
        start_flower_sidecar(spawner)

c.Spawner.pre_spawn_hook = pre_spawn
if FLOWER_SIDECAR:
    c.Spawner.post_stop_hook = stop_flower_sidecar

# ================= MLflow provisioning (was: extra_config.py) =================
MLFLOW_ADMIN = os.environ["MLFLOW_ADMIN_USERNAME"]
MLFLOW_PASS = os.environ["MLFLOW_ADMIN_PASSWORD"]
MLFLOW_SVC = "http://mlflow-svc:5000"
GROUPS_KEY = "oauth_user.roles"
ADMIN_GROUPS = ["mlflow-admin"]

def auth_state_hook(spawner, auth_state):
    if auth_state is None:
        return
    if "MLFLOW_TRACKING_PASSWORD" in spawner.environment:
        spawner.log.info("MLflow: Hook already processed for user. Skipping API cycle.")
        return

    oauth_user = auth_state.get("oauth_user", {})
    username = oauth_user.get("preferred_username")
    password = secrets.token_hex(16)

    try:
        user_roles = auth_state
        for part in GROUPS_KEY.split("."):
            user_roles = user_roles.get(part, {})
        is_admin = any(role in ADMIN_GROUPS for role in user_roles)

        auth_header = base64.b64encode(f"{MLFLOW_ADMIN}:{MLFLOW_PASS}".encode()).decode()
        headers = {"Authorization": f"Basic {auth_header}", "Content-Type": "application/json"}

        res = requests.get(f"{MLFLOW_SVC}/api/2.0/mlflow/users/get",
                           params={"username": username}, headers=headers, timeout=5)
        if res.status_code == 200:
            spawner.log.info(f"MLflow: Updating session password for existing user {username}")
            requests.patch(f"{MLFLOW_SVC}/api/2.0/mlflow/users/update-password",
                           json={"username": username, "password": password}, headers=headers, timeout=5)
        else:
            spawner.log.info(f"MLflow: Provisioning new user {username}")
            requests.post(f"{MLFLOW_SVC}/api/2.0/mlflow/users/create",
                          json={"username": username, "password": password}, headers=headers, timeout=5)
            requests.patch(f"{MLFLOW_SVC}/api/2.0/mlflow/users/update-admin",
                           json={"username": username, "is_admin": is_admin}, headers=headers, timeout=5)

        if not is_admin:
            workspace_name = f"ws-{username}"
            requests.post(f"{MLFLOW_SVC}/api/3.0/mlflow/workspaces",
                          json={"name": workspace_name}, headers=headers, timeout=5)
            res = requests.post(f"{MLFLOW_SVC}/api/3.0/mlflow/roles/create",
                                json={"name": f"{workspace_name}-user", "workspace": workspace_name},
                                headers=headers, timeout=5)
            role_id = res.json()["role"]["id"]
            requests.post(f"{MLFLOW_SVC}/api/3.0/mlflow/roles/permissions/add",
                          json={"permission": "MANAGE", "resource_pattern": "*",
                                "resource_type": "workspace", "role_id": role_id},
                          headers=headers, timeout=5)
            requests.post(f"{MLFLOW_SVC}/api/3.0/mlflow/roles/assign",
                          json={"role_id": role_id, "username": username}, headers=headers, timeout=5)
            spawner.environment["MLFLOW_WORKSPACE"] = workspace_name

        spawner.environment["MLFLOW_TRACKING_USERNAME"] = username
        spawner.environment["MLFLOW_TRACKING_PASSWORD"] = password
        spawner.environment["MLFLOW_TRACKING_URI"] = MLFLOW_SVC
        spawner.environment["MLFLOW_EXTERNAL_TRACKING_URI"] = os.environ["MLFLOW_EXTERNAL_URL"]

        encoded_auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        spawner.environment["PROXY_CONFIG_JSON"] = json.dumps({
            "mlflow": {
                "command": ["socat", "TCP-LISTEN:{port},fork", "TCP:mlflow-svc:5000"],
                "absolute_url": False,
                "request_headers_override": {
                    "Authorization": f"Basic {encoded_auth}",
                    "Host": "mlflow-svc:5000",
                },
                "launcher_entry": {"title": "MLflow UI"},
            },
            "tensorboard": {
                "command": ["tensorboard", "--logdir", "/home/jovyan/logs",
                            "--port", "{port}", "--bind_all"],
                "timeout": 20,
                "launcher_entry": {"title": "TensorBoard"},
            },
        })
    except Exception as e:
        spawner.log.error(f"MLflow Session Provisioning Failed for {username}: {e}")

c.Spawner.auth_state_hook = auth_state_hook