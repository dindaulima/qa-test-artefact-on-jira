"""Jira REST API client — shared auth and request logic."""

import os
import sys
from base64 import b64encode
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: run  source .venv/bin/activate && pip install -r requirements.txt")

try:
    from dotenv import load_dotenv
    # Resolve .env relative to this file: tools/jira/ → project root
    _env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    load_dotenv(dotenv_path=_env_path)
except ImportError:
    pass


def _auth_header() -> dict:
    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    email = os.getenv("JIRA_EMAIL", "")
    token = os.getenv("JIRA_API_TOKEN", "")

    missing = [k for k, v in [
        ("JIRA_BASE_URL", base_url),
        ("JIRA_EMAIL", email),
        ("JIRA_API_TOKEN", token),
    ] if not v]

    if missing:
        sys.exit(f"Missing environment variables: {', '.join(missing)}\n"
                 f"Copy .env.example to .env and fill in your credentials.")

    token_b64 = b64encode(f"{email}:{token}".encode()).decode()
    return {
        "Authorization": f"Basic {token_b64}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def get(path: str, params: dict = None) -> dict:
    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    response = requests.get(
        f"{base_url}/rest/api/3{path}",
        headers=_auth_header(),
        params=params or {},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def put(path: str, payload: dict) -> dict:
    base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
    response = requests.put(
        f"{base_url}/rest/api/3{path}",
        headers=_auth_header(),
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    return response.json() if response.content else {}
