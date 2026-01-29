"""Credential management for NordVPN service credentials."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Credentials:
    """NordVPN service credentials."""

    username: str
    password: str


class CredentialsError(Exception):
    """Error loading credentials."""

    pass


def get_credentials() -> Credentials:
    """Load NordVPN service credentials from environment.

    Looks for NORD_USER and NORD_PASS environment variables.
    Will load from .env file if present.

    Returns:
        Credentials object with username and password

    Raises:
        CredentialsError: If credentials are not configured
    """
    # Load .env file if it exists
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    username = os.getenv("NORD_USER")
    pwd = os.getenv("NORD_PASS")

    if not username or not pwd:
        raise CredentialsError(
            "NordVPN credentials not configured.\n"
            "Set NORD_USER and NORD_PASS environment variables, or create a .env file.\n"
            "Get service credentials from: https://my.nordaccount.com/dashboard/nordvpn/manual-configuration/"
        )

    return Credentials(username=username, password=pwd)


def credentials_configured() -> bool:
    """Check if credentials are configured."""
    try:
        get_credentials()
        return True
    except CredentialsError:
        return False
