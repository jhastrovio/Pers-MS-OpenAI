import json
from pathlib import Path

def get_secrets():
    secrets_path = Path("config/secrets.json")
    if not secrets_path.exists():
        raise FileNotFoundError("Could not find secrets.json at config/secrets.json")
    with open(secrets_path, "r") as f:
        return json.load(f)
