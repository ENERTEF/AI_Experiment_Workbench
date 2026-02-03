import os
import shutil
import logging
import urllib.parse
import sys
import boto3
import psycopg2

logger = logging.getLogger(__name__)
logger.setLevel('INFO')
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
    logger.addHandler(handler)

logger.info("Starting mlflow extension")
def setup_mlflow():
    mlflow_port = 5000
    def get_env():
        return {
            "POSTGRES_HOST":os.environ.get("POSTGRES_HOST","postgres"),
            "POSTGRES_DATABASE":os.environ.get("POSTGRES_DATABASE","mlflow"),
            "POSTGRES_USER":os.environ.get("POSTGRES_USER","mlflow"),
            "POSTGRES_PASSWORD":os.environ.get("POSTGRES_PASSWORD","mlflow"),
            "POSTGRES_PORT":os.environ.get("POSTGRES_PORT","5432"),

            "MINIO_HOST":os.environ.get("MINIO_HOST","minio"),
            "MINIO_BUCKET":os.environ.get("MINIO_BUCKET","mlflow"),
            "MINIO_USER":os.environ.get("MINIO_USER","mlflow"),
            "MINIO_PASSWORD":os.environ.get("MINIO_PASSWORD","mlflow"),
            "MINIO_PORT":os.environ.get("MINIO_PORT","9000"),

            "USERNAME":os.environ.get("JUPYTERHUB_USER","default")
        }
    """Setup commands and icon paths and return a dictionary compatible with jupyter-server-proxy."""
    def _get_icon_path():
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'icons', 'mlflow.svg'
        )

    def ensure_s3_prefix(
        username,
        host,
        port,
        bucket,
        user,
        password
    ):
        try:
            s3 = boto3.client('s3',
                endpoint_url=f'http://{host}:{port}',
                aws_access_key_id=user,
                aws_secret_access_key=password
            )
            logger.info(f"Creating bucket prefix: {bucket}/{username}")
            s3.put_object(Bucket=bucket, Key=f"{username}/")
            logger.info(f"Successfully created: {bucket}/{username}")
        except Exception as e:
            logger.error(f"Error creating bucket prefix {bucket}/{username}: {e}")

    def ensure_postgres_schema(
        username,
        host,
        port,
        database,
        user,
        password
    ):
        try:
            conn = psycopg2.connect(
                host=host,
                dbname=database,
                port=port,
                user=user,
                password=password
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Create user schema
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {username}")
            logger.info(f"Created schema for user: {username}")
                        
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error creating PostgreSQL schemas: {e}")

    def _get_mlflow_command(port):
        executable = shutil.which('mlflow')
        if not executable:
            raise FileNotFoundError('Cannot find mlflow executable in $PATH')
        env = get_env()
        username = env['USERNAME']
        ensure_s3_prefix(
            username,
            env['MINIO_HOST'],
            env['MINIO_PORT'],
            env['MINIO_BUCKET'],
            env['MINIO_USER'],
            env['MINIO_PASSWORD']
        )
        ensure_postgres_schema(
            username,
            env['POSTGRES_HOST'],
            env['POSTGRES_PORT'],
            env['POSTGRES_DATABASE'],
            env['POSTGRES_USER'],
            env['POSTGRES_PASSWORD']
        )
        
        schema_list = [username]
        search_path = ','.join(schema_list)
        password = urllib.parse.quote(env['POSTGRES_PASSWORD'])
        options = urllib.parse.quote(f"-csearch_path={search_path}")
        backend_store = f"postgresql://{env['POSTGRES_USER']}:{password}@{env['POSTGRES_HOST']}:{env['POSTGRES_PORT']}/{env['POSTGRES_DATABASE']}?options={options}"
        artifact_uri = f"s3://{env['MINIO_BUCKET']}/{username}"
        logger.info(f"Artifact route: {artifact_uri}")
        logger.info(f"Backend store: {backend_store}")
        
        return [
            'mlflow', 'server',
            '--host', '0.0.0.0',
            '--allowed-hosts', '*',
            '--port', str(port),
            '--backend-store-uri', backend_store,
            '--default-artifact-root', artifact_uri
        ]

    return {
        'command': _get_mlflow_command,
        'port': mlflow_port,
        'timeout': 20,
        'new_browser_tab': True,
        'launcher_entry': {
            'title': 'MLflow',
            'icon_path': _get_icon_path()
        },
    }