import os
import shutil
import logging
import boto3
import psycopg2

logger = logging.getLogger(__name__)
logger.setLevel('INFO')

def setup_mlflow():
    """Setup commands and icon paths and return a dictionary compatible with jupyter-server-proxy."""
    def _get_icon_path():
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'icons', 'mlflow.svg'
        )

    def ensure_s3_prefix(bucket, prefix):
        try:
            s3 = boto3.client('s3',
                endpoint_url=os.environ.get('MLFLOW_S3_ENDPOINT_URL', "http://minio.minio-tenant:80"),
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
            )
            print(f"Creating bucket prefix: {bucket}/{prefix}")
            s3.put_object(Bucket=bucket, Key=f"{prefix}/")
            print(f"Successfully created: {bucket}/{prefix}")
        except Exception as e:
            print(f"Error creating bucket prefix {bucket}/{prefix}: {e}")

    def ensure_postgres_schema(username):
        try:
            conn = psycopg2.connect(
                host=os.environ.get('POSTGRES_HOST', 'db'),
                database='mlflow',
                user=os.environ.get('POSTGRES_USER', 'mlflow'),
                password=os.environ.get('POSTGRES_PASSWORD', 'mlflow')
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Create user schema
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {username}")
            print(f"Created schema for user: {username}")
                        
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error creating PostgreSQL schemas: {e}")

    def _get_mlflow_command(port):
        executable = shutil.which('mlflow')
        if not executable:
            raise FileNotFoundError('Cannot find mlflow executable in $PATH')
        
        username = os.environ.get('JUPYTERHUB_USER', 'default')
        
        print(f"Setting up MLflow for user: {username}")
        ensure_s3_prefix('mlflow', f'{username}/')
        ensure_postgres_schema(username)
        
        schema_list = [username]
        search_path = ','.join(schema_list)
        backend_store = f'postgresql://mlflow:mlflow@db:5432/mlflow?options=-csearch_path={search_path}'
        artifact_root = f's3://mlflow/{username}'
        print(f"Artifact directory: {artifact_root}")  # Changed from logger.info
        print(f"Backend store: {backend_store}")       # Changed from logger.info
        logger.info(f"Artifact route: {artifact_root}")
        logger.info(f"Backend store: {backend_store}")
        
        return [
            'mlflow', 'server',
            '--host', '0.0.0.0',
            '--port', str(port),
            '--backend-store-uri', backend_store,
            '--default-artifact-root', artifact_root
        ]

    return {
        'command': _get_mlflow_command,
        'port': 5000,
        'timeout': 20,
        'new_browser_tab': True,
        'launcher_entry': {
            'title': 'MLflow',
            'icon_path': _get_icon_path()
        },
    }