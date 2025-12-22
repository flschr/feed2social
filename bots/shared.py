"""
Shared utilities for Bear Blog automation bots.
"""

import os
import re
import logging
import yaml
import requests
from pathlib import Path
from time import sleep
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter, Retry

# --- LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# --- CONFIG ---
def load_config() -> dict:
    """Load configuration from central config.yaml file."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


CONFIG = load_config()


# --- CONSTANTS ---
REQUEST_TIMEOUT = 15  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds
MAX_IMAGE_SIZE = 10_000_000  # 10MB
MAX_CSV_SIZE = 50_000_000  # 50MB
MAX_WORKERS = 5  # Concurrent operations


# --- EXCEPTIONS ---
class BotException(Exception):
    """Base exception for all bot errors."""
    pass


class AuthenticationError(BotException):
    """Raised when authentication fails."""
    pass


class ConfigurationError(BotException):
    """Raised when configuration is invalid."""
    pass


class DownloadError(BotException):
    """Raised when download fails."""
    pass


# --- SECURITY ---
def is_safe_url(url: str) -> bool:
    """Validate that the URL uses a safe protocol (HTTP/HTTPS)."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            logger.warning(f"Rejected URL with unsafe protocol: {parsed.scheme}")
            return False
        return True
    except Exception as e:
        logger.warning(f"Error validating URL: {e}")
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.
    Returns only the basename without any directory components.
    """
    filename = os.path.basename(filename)
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    if filename.startswith('.'):
        filename = '_' + filename
    if not filename or len(filename) > 255:
        filename = 'image.webp'
    return filename


def clean_filename(text: str) -> str:
    """
    Creates a safe filename for files and folders.
    Removes special characters and emojis.
    """
    text = re.sub(r'[^\w\s-]', '', str(text)).strip().lower()
    text = re.sub(r'[-\s]+', '-', text)
    return text[:100]


# --- HTTP ---
def create_session(user_agent: str = 'bearblog-bot/2.0') -> requests.Session:
    """Create a requests session with connection pooling and retry logic."""
    session = requests.Session()
    session.headers.update({'User-Agent': user_agent})

    adapter = HTTPAdapter(
        pool_connections=10,
        pool_maxsize=20,
        max_retries=Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_BACKOFF,
            status_forcelist=[500, 502, 503, 504]
        )
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    return session


# --- FILE LOCKING ---
class FileLock:
    """Simple file-based lock with exponential backoff."""

    def __init__(self, lock_path: Path, max_retries: int = 10, initial_backoff: float = 0.5):
        self.lock_path = lock_path
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff

    def acquire(self) -> bool:
        """Acquire the lock with exponential backoff."""
        retry = 0
        backoff = self.initial_backoff

        while self.lock_path.exists() and retry < self.max_retries:
            sleep(backoff)
            backoff *= 1.5
            retry += 1

        if self.lock_path.exists():
            raise TimeoutError(f"Could not acquire lock after {self.max_retries} retries")

        self.lock_path.touch()
        return True

    def release(self) -> None:
        """Release the lock."""
        if self.lock_path.exists():
            self.lock_path.unlink()

    def __enter__(self) -> 'FileLock':
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
