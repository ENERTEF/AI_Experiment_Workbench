import os
import datetime
from keras import callbacks


class TensorBoardLogger:
    def __init__(self, base_log_dir='/home/jovyan/logs', experiment_name='experiment'):
        """
        Initializes the TensorBoardLogger.

        :param base_log_dir: Base directory for logs. Default is /logs which is the shared volume in JupyterHub.
        :param experiment_name: Name of the experiment for logging.
        """
        # Get username from environment to create user-specific log directories
        username = os.environ.get('JUPYTERHUB_USER', 'default-user')
        timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        
        # Create user-specific log directory in the shared volume
        self.log_dir = os.path.join(base_log_dir, username, experiment_name, timestamp)
        os.makedirs(self.log_dir, exist_ok=True)
        self.callback = callbacks.TensorBoard(log_dir=self.log_dir, 
                                              histogram_freq=1,
                                              write_graph=True,
                                              write_images=True,
                                              update_freq='epoch')
    
    def get_callback(self):
        """
        Returns the TensorBoard callback.

        :return: TensorBoard callback instance.
        """
        return self.callback

    def summary(self):
        """
        Prints the summary of the logging directory.

        :return: None
        """
        print(f"TensorBoard logs will be saved to: {self.log_dir}")

    def clear_logs(self):
        """
        Clears the logs directory.

        :return: None
        """
        if os.path.exists(self.log_dir):
            for file in os.listdir(self.log_dir):
                file_path = os.path.join(self.log_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            print(f"Cleared logs in: {self.log_dir}")
        else:
            print(f"No logs found at: {self.log_dir}")