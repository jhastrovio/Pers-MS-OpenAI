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
    # Azure configuration
    "azure": {
        "client_id": get_env_variable('CLIENT_ID'),
        "client_secret": get_env_variable('CLIENT_SECRET'),
        "tenant_id": get_env_variable('TENANT_ID')
    },
    
    # User configuration
    "user": {
        "email": get_env_variable('USER_EMAIL')
    },
    
    # OpenAI configuration
    "openai": {
        "api_key": get_env_variable('OPENAI_API_KEY'),
        "vector_store_id": get_env_variable('OPENAI_VECTOR_STORE_ID'),
        "vector_store_name":get_env_variable('OPENAI_VECTOR_STORE_NAME')
    },
    
    # OneDrive configuration
    "onedrive": {
        "file_list": "data_PMSA/processing_list.json",
        "emails_folder": "data_PMSA/emails_1",
        "documents_folder": "data_PMSA/documents_1",
        "attachments_folder": "data_PMSA/attachments_1",
        "processed_emails_folder": "data_PMSA/processed_emails_2",
        "processed_documents_folder": "data_PMSA/processed_documents_2"
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

# Consolidated processing configuration used by processing_1_2_0 module
PROCESSING_CONFIG = {
    "MAX_FILE_SIZE": config["processing"]["MAX_FILE_SIZE"],
    "MAX_ATTACHMENT_SIZE": config["processing"]["MAX_ATTACHMENT_SIZE"],
    "ALLOWED_EXTENSIONS": config["processing"]["ALLOWED_EXTENSIONS"],
    "CONTENT_TYPES": config["processing"]["CONTENT_TYPES"],
    "TEXT_CLEANING": config["processing"]["TEXT_CLEANING"],
    "METADATA": config["processing"]["METADATA"],
    "FOLDERS": {
        "EMAILS": config["onedrive"]["emails_folder"],
        "DOCUMENTS": config["onedrive"]["documents_folder"],
        "ATTACHMENTS": config["onedrive"]["attachments_folder"],
        "PROCESSED_EMAILS": config["onedrive"]["processed_emails_folder"],
        "PROCESSED_DOCUMENTS": config["onedrive"]["processed_documents_folder"],
        "FILE_LIST": config["onedrive"]["file_list"]
    },
    "user": {
        "email": config["user"]["email"]
    },
    # Enhanced extraction configuration
    "ENHANCED_EXTRACTION": {
        "ENABLED": True,  # Master switch for enhanced extraction
        "USE_LAYOUT_ANALYSIS": True,  # Use pdfplumber for better PDF layout detection
        "CHUNK_DOCUMENTS": True,  # Enable semantic chunking
        "CHUNK_SIZE": 500,  # Target chunk size in tokens
        "CHUNK_OVERLAP": 75,  # Overlap between chunks in tokens
        "REMOVE_HEADERS_FOOTERS": True,  # Clean repetitive headers/footers
        "REMOVE_PAGE_NUMBERS": True,  # Remove page number patterns
        "REMOVE_BOILERPLATE": True,  # Remove common boilerplate text
        "NORMALIZE_WHITESPACE": True,  # Fix whitespace and hyphenation
        "FIX_ENCODING": True,  # Fix smart quotes, ligatures, etc.
        "USE_OCR_FALLBACK": True,  # Use OCR for scanned documents
        "OCR_CONFIDENCE_THRESHOLD": 0.7,  # Minimum OCR confidence
        "PRESERVE_STRUCTURE": True,  # Maintain document structure in chunks
        "PRESERVE_HEADINGS": True,  # Track heading hierarchy in chunks
    }
}

# Example usage
# client_id = get_env_variable('CLIENT_ID')
# client_secret = get_env_variable('CLIENT_SECRET')
# tenant_id = get_env_variable('TENANT_ID')
# user_email = get_env_variable('USER_EMAIL')
