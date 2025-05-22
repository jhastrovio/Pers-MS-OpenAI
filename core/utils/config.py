"""Configuration utilities and settings model."""

import os
from functools import lru_cache
from dotenv import load_dotenv
from pydantic import BaseSettings, Field
from typing import Any, Dict, List, Set

load_dotenv()


def get_env_variable(key: str, default: str | None = None) -> str | None:
    """Return environment variable or default."""
    return os.getenv(key, default)


class AzureSettings(BaseSettings):
    client_id: str | None = Field(default=None, env="CLIENT_ID")
    client_secret: str | None = Field(default=None, env="CLIENT_SECRET")
    tenant_id: str | None = Field(default=None, env="TENANT_ID")


class UserSettings(BaseSettings):
    email: str | None = Field(default=None, env="USER_EMAIL")


class OpenAISettings(BaseSettings):
    api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    vector_store_id: str | None = Field(default=None, env="OPENAI_VECTOR_STORE_ID")
    vector_store_name: str | None = Field(default=None, env="OPENAI_VECTOR_STORE_NAME")


class OneDriveSettings(BaseSettings):
    file_list: str = "data_PMSA/processing_list.json"
    emails_folder: str = "data_PMSA/emails_1"
    documents_folder: str = "data_PMSA/documents_1"
    attachments_folder: str = "data_PMSA/attachments_1"
    processed_emails_folder: str = "data_PMSA/processed_emails_2"
    processed_documents_folder: str = "data_PMSA/processed_documents_2"
    processed_chunk_dir: str = "data_PMSA/processed_chunks"
    embeddings_dir: str = "data_PMSA/embeddings"
    logs_dir: str = "data_PMSA/logs"


class ProcessingSettings(BaseSettings):
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    MAX_ATTACHMENT_SIZE: int = 25 * 1024 * 1024  # 25MB
    ALLOWED_EXTENSIONS: Set[str] = {
        ".pdf",
        ".docx",
        ".doc",
        ".pptx",
        ".ppt",
        ".xlsx",
        ".xls",
        ".csv",
        ".txt",
        ".html",
    }
    CONTENT_TYPES: List[str] = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
        "text/html",
    ]
    TEXT_CLEANING: Dict[str, bool] = {
        "REMOVE_EXTRA_WHITESPACE": True,
        "NORMALIZE_LINE_ENDINGS": True,
        "REMOVE_CONTROL_CHARS": True,
    }
    METADATA: Dict[str, bool] = {
        "EXTRACT_AUTHOR": True,
        "EXTRACT_DATE": True,
        "EXTRACT_TITLE": True,
    }


class AppConfig(BaseSettings):
    azure: AzureSettings = AzureSettings()
    user: UserSettings = UserSettings()
    openai: OpenAISettings = OpenAISettings()
    onedrive: OneDriveSettings = OneDriveSettings()
    processing: ProcessingSettings = ProcessingSettings()

    @property
    def processing_config(self) -> Dict[str, Any]:
        return {
            "MAX_FILE_SIZE": self.processing.MAX_FILE_SIZE,
            "MAX_ATTACHMENT_SIZE": self.processing.MAX_ATTACHMENT_SIZE,
            "ALLOWED_EXTENSIONS": self.processing.ALLOWED_EXTENSIONS,
            "CONTENT_TYPES": self.processing.CONTENT_TYPES,
            "TEXT_CLEANING": self.processing.TEXT_CLEANING,
            "METADATA": self.processing.METADATA,
            "FOLDERS": {
                "EMAILS": self.onedrive.emails_folder,
                "DOCUMENTS": self.onedrive.documents_folder,
                "ATTACHMENTS": self.onedrive.attachments_folder,
                "PROCESSED_EMAILS": self.onedrive.processed_emails_folder,
                "PROCESSED_DOCUMENTS": self.onedrive.processed_documents_folder,
                "PROCESSED_CHUNKS": self.onedrive.processed_chunk_dir,
                "EMBEDDINGS": self.onedrive.embeddings_dir,
                "LOGS": self.onedrive.logs_dir,
                "FILE_LIST": self.onedrive.file_list,
            },
            "user": {"email": self.user.email},
        }


@lru_cache(maxsize=1)
def load_config() -> AppConfig:
    """Load and cache application configuration."""
    return AppConfig()


# Instantiate a module level config for convenience
app_config = load_config()
CONTENT_TYPES = app_config.processing.CONTENT_TYPES
PROCESSING_CONFIG = app_config.processing_config

__all__ = [
    "app_config",
    "PROCESSING_CONFIG",
    "CONTENT_TYPES",
    "get_env_variable",
    "load_config",
]
