"""
Configuration module for the application.
"""

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

# Content types
CONTENT_TYPES = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain',
    'text/html',
]

# File size limits (in bytes)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024  # 25MB

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    '.pdf', '.docx', '.doc', '.pptx', '.ppt', 
    '.xlsx', '.xls', '.csv', '.txt', '.html'
}

# Main configuration dictionary
config = {
    # OneDrive configuration
    "onedrive": {
        "emails_folder": "data_PMSA/emails_1",
        "documents_folder": "data_PMSA/documents_1",
        "processed_emails_folder": "data_PMSA/processed_emails_2",
        "processed_documents_folder": "data_PMSA/processed_documents_2",
        "processed_chunk_dir": "data_PMSA/processed_chunks",
        "embeddings_dir": "embeddings",
        "logs_dir": "logs"
    },
    
    # Processing configuration
    "processing": {
        "MAX_FILE_SIZE": MAX_FILE_SIZE,
        "MAX_ATTACHMENT_SIZE": MAX_ATTACHMENT_SIZE,
        "ALLOWED_EXTENSIONS": ALLOWED_EXTENSIONS,
        "CONTENT_TYPES": CONTENT_TYPES,
        "TEXT_CLEANING": {
            "REMOVE_EXTRA_WHITESPACE": True,
            "NORMALIZE_LINE_ENDINGS": True,
            "REMOVE_CONTROL_CHARS": True
        },
        "METADATA": {
            "EXTRACT_AUTHOR": True,
            "EXTRACT_DATE": True,
            "EXTRACT_TITLE": True
        }
    }
}

# Example usage
# client_id = get_env_variable('CLIENT_ID')
# client_secret = get_env_variable('CLIENT_SECRET')
# tenant_id = get_env_variable('TENANT_ID')
# user_email = get_env_variable('USER_EMAIL')
