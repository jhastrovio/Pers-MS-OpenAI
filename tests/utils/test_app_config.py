import os
from core.utils.config import load_config


def test_app_config_defaults(monkeypatch):
    load_config.cache_clear()
    cfg = load_config()
    assert cfg.onedrive.file_list == "data_PMSA/processing_list.json"


def test_app_config_env_override(monkeypatch):
    monkeypatch.setenv("USER_EMAIL", "override@example.com")
    load_config.cache_clear()
    cfg = load_config()
    assert cfg.user.email == "override@example.com"
