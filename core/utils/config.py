import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_env_variable(key, default=None):
    """Get an environment variable.

    Args:
        key: The name of the environment variable.
        default: The default value to return if the variable is not set.

    Returns:
        The value of the environment variable, or the default if not set.
    """
    return os.getenv(key, default)

# Example usage
# client_id = get_env_variable('CLIENT_ID')
# client_secret = get_env_variable('CLIENT_SECRET')
# tenant_id = get_env_variable('TENANT_ID')
# user_email = get_env_variable('USER_EMAIL')

# Add the following lines to the config.yaml file
config = {
    "onedrive": {
        "emails_folder": "data_PMSA/emails_1",
        "documents_folder": "data_PMSA/documents_1",
        "processed_emails_folder": "data_PMSA/processed_emails_2",
        "processed_documents_folder": "data_PMSA/processed_documents_2",
        "processed_chunk_dir": "data_PMSA/processed_chunks",
        "embeddings_dir": "embeddings",
        "logs_dir": "logs"
    }
}
