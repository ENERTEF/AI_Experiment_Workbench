# Visual Workflow
## Access and Login

### 1. JupyterHub Login
Access the platform at `http://localhost:8080` to begin your ML development session.

![JupyterHub Login Page](images/01_jupyterhub_login_page.png)

### 2. User Session Loading
After authentication, the platform prepares your personalized environment.

![User Loading Screen](images/02_user_loading.png)

## Jupyter Environment

### 3. Welcome and Pre-loaded Scripts
Your notebook environment starts with pre-configured scripts and welcome materials.

![Jupyter Welcome Script](images/03_jupyter_welcome_script.png)

### 4. Available Extensions
The platform includes integrated extensions for ML tools accessible directly from your notebook.

![Available Extensions](images/04_extensions.png)

## ML Tool Integration

### 5. MLflow Extension
Track experiments, log parameters, and manage models through the integrated MLflow interface.

![MLflow Extension](images/05_mlflow_extension.png)

### 6. MLflow Example Code
Example code showing how to track parameters, metrics, and artifacts with MLflow.

![MLflow Example Code](images/06_mlflow_example.png)

### 7. MLflow Interface After Run
The MLflow interface displaying the tracked experiment after code execution.

![MLflow Interface](images/07_mlflow_interface_after_example.png)

### 8. MLflow Run Details
Detailed view of an MLflow experiment run with parameters, metrics, and artifacts.

![MLflow Run Details](images/08_mlflow_run.png)

View of saved models.

![MLflow registered models](images/09_mlflow_models_saved.png)

### 9. TensorBoard Extension
Visualize training metrics and model performance with the integrated TensorBoard interface.

![TensorBoard Extension](images/09_tensorboard_extension.png)

### 10. TensorBoard Example Run
Example of a model training run being visualized in TensorBoard.

![TensorBoard Run](images/10_tensorboard_run.png)

### 11. TensorBoard Logs
Training metrics visualized as graphs in the TensorBoard interface.

![TensorBoard Logs](images/11_tensorboard_logs.png)

### 12. TensorBoard Model Graph
Visual representation of the neural network architecture in TensorBoard.

![TensorBoard Model Graph](images/12_tensorboard_model_graph.png)

## Database Management

### 13. pgAdmin Access
Manage PostgreSQL databases through the web-based pgAdmin interface at `http://localhost:5050`.

![pgAdmin Login](images/13_pgadmin_login_page.png)

### 14. Database Authentication
Enter database credentials to access your data.

![Database Password](images/14_database_pwd.png)

### 15. Database Interface
Navigate and manage database schemas and tables.

![pgAdmin Interface](images/15_pgadmin_after_login.png)

### 16. Database Overview
View all available databases in your environment.

![Databases View](images/16_database_after_login.png)

### 17. Database Structure
Explore individual database schemas and objects.

![Database Structure](images/17_databases.png)

### 18. MLflow Database
Access the dedicated MLflow database for experiment metadata.

![MLflow Database](images/18_mlflow_database.png)

### 19. MLflow data saved
Access the saved data in the MLflow database.

![Mlflow Postgres](images/18_postgres.png)


## Object Storage

### 20. MinIO Console
Manage datasets, models, and artifacts through the MinIO interface at `http://localhost:9001`.

![MinIO Login](images/19_minio.png)

### 21. MinIO Dashboard
Browse and organize your stored data and model artifacts.

![MinIO Interface](images/20_minio_after_login.png)

### 22. MinIO saved models
Browse saved models in MinIO.

![MinIO saved model](images/21_minio_saved_model.png)

### 23. MinIO saved plots
Browse saved artifacts (plots) in MinIO.

![MinIO saved plots](images/22_minio_saved_plot.png)

## Workflow Summary

1. **Login** → Access JupyterHub interface
2. **Environment Setup** → Automatic provisioning of notebook with extensions
3. **Development** → Use integrated MLflow and TensorBoard for experiment tracking
4. **Data Management** → Store and retrieve data via MinIO
5. **Database Access** → Query and manage data through pgAdmin
6. **Collaboration** → Share experiments and models across the platform

## Service Endpoints

- **JupyterHub**: http://localhost:8080
- **MinIO Console**: http://localhost:9001
- **pgAdmin**: http://localhost:5050
- **MLflow UI**: Accessible via Jupyter extension
- **TensorBoard**: Accessible via Jupyter extension

This visual workflow demonstrates the complete user experience from initial login through active development and data management.