"""
Social media bot for automating posts from RSS feeds to Bluesky and Mastodon.
Includes security hardening, performance optimizations, and improved error handling.
"""

import feedparser
import json
import os
import re
import requests
import logging
import tempfile
import hashlib
import yaml
from typing import Optional, Dict, List, Set, Any
from pathlib import Path
from bs4 import BeautifulSoup
from atproto import Client, client_utils, models
from mastodon import Mastodon
from contextlib import contextmanager
from time import sleep
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- LOAD CONFIG ---
def load_config() -> dict:
    """Load configuration from central config.yaml file."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()
MASTODON_INSTANCE = CONFIG['social']['mastodon_instance']

# --- CONSTANTS ---
MAX_IMAGE_SIZE = 5_000_000
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # Seconds
MAX_WORKERS = 3  # For concurrent operations

PLATFORM_BLUESKY = "bluesky"
PLATFORM_MASTODON = "mastodon"

BASE_DIR = Path(__file__).parent.absolute()
POSTED_FILE = BASE_DIR / 'posted_articles.txt'
LOCK_FILE = BASE_DIR / 'posted_articles.txt.lock'
CONFIG_FILE = BASE_DIR / 'config.json'
FEED_CACHE_FILE = BASE_DIR / 'feed_cache.json'

# Session configuration
session = requests.Session()
session.headers.update({'User-Agent': 'feed2social/2.0'})
# Connection pooling for better performance
adapter = requests.adapters.HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=requests.adapters.Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=[500, 502, 503, 504]
    )
)
session.mount('http://', adapter)
session.mount('https://', adapter)


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


@contextmanager
def posted_file_lock():
    """
    Simple file lock to prevent concurrent write access to the posted file.
    Uses exponential backoff for retries.
    """
    retry = 0
    max_retries = 10
    backoff = 0.5

    while LOCK_FILE.exists() and retry < max_retries:
        sleep(backoff)
        backoff *= 1.5  # Exponential backoff
        retry += 1

    if LOCK_FILE.exists():
        raise TimeoutError(f"Could not acquire lock after {max_retries} retries")

    try:
        LOCK_FILE.touch()
        yield
    finally:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()


def load_feed_cache() -> Dict[str, Dict[str, str]]:
    """
    Load feed cache containing ETag and Last-Modified headers.
    Returns a dict mapping feed URLs to their cache headers.
    """
    if not FEED_CACHE_FILE.exists():
        return {}

    try:
        with open(FEED_CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading feed cache: {e}")
        return {}


def save_feed_cache(cache: Dict[str, Dict[str, str]]) -> None:
    """Save feed cache to disk."""
    try:
        with open(FEED_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving feed cache: {e}")


def check_feed_changed(feed_url: str, cache: Dict[str, Dict[str, str]]) -> tuple[bool, Dict[str, str]]:
    """
    Check if a feed has changed using HEAD request with ETag/Last-Modified.

    Returns:
        (has_changed, new_headers): Tuple of boolean and dict with new cache headers
    """
    try:
        # Make HEAD request to check for changes
        response = session.head(feed_url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        response.raise_for_status()

        new_headers = {
            'etag': response.headers.get('ETag', ''),
            'last-modified': response.headers.get('Last-Modified', '')
        }

        # If we have no cached headers, assume it changed
        if feed_url not in cache:
            logger.info(f"No cache for {feed_url}, will fetch")
            return True, new_headers

        cached_headers = cache[feed_url]

        # Compare ETag first (more reliable)
        if new_headers['etag'] and cached_headers.get('etag'):
            if new_headers['etag'] == cached_headers['etag']:
                logger.info(f"Feed unchanged (ETag match): {feed_url}")
                return False, new_headers

        # Compare Last-Modified
        if new_headers['last-modified'] and cached_headers.get('last-modified'):
            if new_headers['last-modified'] == cached_headers['last-modified']:
                logger.info(f"Feed unchanged (Last-Modified match): {feed_url}")
                return False, new_headers

        # If neither header is present or they differ, assume changed
        logger.info(f"Feed changed or no cache headers: {feed_url}")
        return True, new_headers

    except requests.exceptions.RequestException as e:
        logger.warning(f"Error checking feed headers for {feed_url}: {e}")
        # On error, assume changed to avoid missing updates
        return True, {}
    except Exception as e:
        logger.error(f"Unexpected error checking feed: {e}")
        return True, {}


def load_posted_articles() -> Set[str]:
    """
    Load all posted article URLs into memory for fast lookup.
    Returns a set for O(1) lookup time.
    """
    if not POSTED_FILE.exists():
        return set()

    try:
        with posted_file_lock():
            with open(POSTED_FILE, 'r', encoding='utf-8') as f:
                return {line.strip() for line in f if line.strip()}
    except Exception as e:
        logger.error(f"Error loading posted articles: {e}")
        return set()


def is_posted(link: str, posted_cache: Set[str]) -> bool:
    """Check if the given URL is already recorded in the posted cache."""
    return link in posted_cache


def mark_as_posted(link: str) -> None:
    """Add a URL to the posted.txt file (prepends to keep newest on top)."""
    try:
        with posted_file_lock():
            # Read existing entries
            existing_lines = []
            if POSTED_FILE.exists():
                with open(POSTED_FILE, 'r', encoding='utf-8') as f:
                    existing_lines = f.readlines()

            # Write new entry at the top, followed by existing entries
            with open(POSTED_FILE, 'w', encoding='utf-8') as f:
                f.write(link + '\n')
                f.writelines(existing_lines)

        logger.info(f"Marked as posted (prepended): {link}")
    except Exception as e:
        logger.error(f"Error marking as posted: {e}")
        raise


def get_html_content(entry: Any) -> str:
    """Extract text from HTML, remove images, and clean up redundant whitespace."""
    try:
        html = entry.content[0].value if hasattr(entry, 'content') else entry.get('summary', '')
        soup = BeautifulSoup(html, "html.parser")

        # Remove all image tags
        for img in soup.find_all('img'):
            img.decompose()

        # Extract plain text with a space separator
        text = soup.get_text(separator=' ')

        # Whitespace cleaning
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs -> single space
        text = re.sub(r'\n\s*\n', '\n\n', text)  # Multiple newlines -> double newline
        return text.strip()
    except Exception as e:
        logger.warning(f"Error extracting HTML content: {e}")
        return ""


def is_safe_image_url(url: str) -> bool:
    """Validate that the image URL uses a safe protocol (HTTP/HTTPS)."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ('http', 'https')
    except Exception:
        return False


def get_first_image_data(entry: Any) -> Optional[Dict[str, str]]:
    """Extract the first image URL and its alt text from the post."""
    try:
        html = entry.content[0].value if hasattr(entry, 'content') else entry.get('summary', '')
        soup = BeautifulSoup(html, "html.parser")
        img = soup.find('img')

        if img and img.get('src'):
            img_url = img.get('src')

            # Security: validate URL
            if not is_safe_image_url(img_url):
                return None

            return {
                "url": img_url,
                "alt": img.get('alt', '')[:400]
            }
        return None
    except Exception as e:
        logger.warning(f"Error extracting image data: {e}")
        return None


def download_image(img_url: str) -> Optional[str]:
    """
    Download an image to a temporary file while respecting size limits.
    Returns the path to the temporary file, or None on failure.
    Uses secure temporary file creation.
    """
    try:
        # Security check
        if not is_safe_image_url(img_url):
            logger.warning(f"Rejected unsafe image URL: {img_url}")
            return None

        # Create secure temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode='wb',
            suffix='.jpg',
            delete=False,
            dir=BASE_DIR
        )

        try:
            r = session.get(img_url, timeout=REQUEST_TIMEOUT, stream=True)
            r.raise_for_status()

            # Check content length
            content_length = int(r.headers.get('content-length', 0))
            if content_length > MAX_IMAGE_SIZE:
                logger.warning(f"Image too large: {content_length} bytes")
                temp_file.close()
                os.unlink(temp_file.name)
                return None

            # Download with size check
            total_downloaded = 0
            for chunk in r.iter_content(chunk_size=8192):
                total_downloaded += len(chunk)
                if total_downloaded > MAX_IMAGE_SIZE:
                    logger.warning(f"Image download exceeded size limit")
                    temp_file.close()
                    os.unlink(temp_file.name)
                    return None
                temp_file.write(chunk)

            temp_file.close()
            return temp_file.name

        except Exception as e:
            temp_file.close()
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
            raise

    except requests.exceptions.RequestException as e:
        logger.warning(f"Error downloading image from {img_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading image: {e}")
        return None


def get_og_metadata(url: str) -> Optional[Dict[str, Optional[str]]]:
    """Fetch Open Graph metadata (title, description, image) for a given link."""
    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, 'html.parser')

        title_tag = soup.find("meta", property="og:title")
        desc_tag = soup.find("meta", property="og:description")
        img_tag = soup.find("meta", property="og:image")

        return {
            "title": title_tag["content"] if title_tag else "Blog post",
            "description": desc_tag["content"] if desc_tag else "",
            "image_url": img_tag["content"] if img_tag else None
        }
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error fetching OG metadata from {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching OG metadata: {e}")
        return None


def submit_to_indexnow(url: str) -> None:
    """Submit the URL to IndexNow for faster search engine indexing."""
    key = os.getenv('INDEXNOW_KEY')
    if not key:
        return

    payload = {
        "host": "fischr.org",
        "key": key,
        "urlList": [url]
    }

    try:
        response = session.post(
            "https://www.bing.com/indexnow",
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        logger.info(f"IndexNow success for {url}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"IndexNow request failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in IndexNow submission: {e}")


def post_to_bluesky(text: str, img_path: Optional[str], alt_text: str, link: Optional[str] = None) -> None:
    """Post rich text to Bluesky, converting hashtags and links into clickable facets with link card preview."""
    handle = os.getenv('BSKY_HANDLE')
    password = os.getenv('BSKY_PW')

    if not handle or not password:
        raise AuthenticationError("BSKY_HANDLE or BSKY_PW environment variables not set")

    try:
        client = Client()
        client.login(handle, password)

        # TextBuilder automatically handles rich text facets (hashtags, links)
        tb = client_utils.TextBuilder()

        # Split text to identify tags and links for rich text processing
        words = text.split(' ')
        for i, word in enumerate(words):
            if word.startswith('#') and len(word) > 1:
                tag_name = word[1:].rstrip('.,!?')
                tb.tag(word, tag_name)
            elif word.startswith('http'):
                tb.link(word, word)
            else:
                tb.text(word)

            # Add space back if it's not the last word
            if i < len(words) - 1:
                tb.text(' ')

        embed = None

        # Prefer external link card with OG preview over image embed
        if link:
            try:
                og_data = get_og_metadata(link)
                if og_data:
                    # Download OG image if available
                    thumb_blob = None
                    if og_data.get('image_url'):
                        og_img_path = download_image(og_data['image_url'])
                        if og_img_path and os.path.exists(og_img_path):
                            try:
                                with open(og_img_path, 'rb') as f:
                                    thumb_blob = client.upload_blob(f.read()).blob
                            except Exception as e:
                                logger.warning(f"Error uploading OG image: {e}")
                            finally:
                                # Clean up OG image
                                if og_img_path and os.path.exists(og_img_path):
                                    try:
                                        os.unlink(og_img_path)
                                    except Exception as e:
                                        logger.warning(f"Error removing OG image file: {e}")

                    # Create external link card embed
                    embed = models.AppBskyEmbedExternal.Main(
                        external=models.AppBskyEmbedExternal.External(
                            title=og_data.get('title', 'Blog post')[:300],
                            description=og_data.get('description', '')[:1000],
                            uri=link,
                            thumb=thumb_blob
                        )
                    )
                    logger.info("Created external link card embed for Bluesky")
            except Exception as e:
                logger.warning(f"Error creating external embed: {e}")
                # Fall back to image embed if link card fails

        # If no link card was created, use image embed as fallback
        if embed is None and img_path and os.path.exists(img_path):
            try:
                with open(img_path, 'rb') as f:
                    upload = client.upload_blob(f.read())
                    embed = models.AppBskyEmbedImages.Main(
                        images=[models.AppBskyEmbedImages.Image(
                            alt=alt_text or "",
                            image=upload.blob
                        )]
                    )
            except Exception as e:
                logger.error(f"Error uploading image to Bluesky: {e}")
                # Continue without image

        client.send_post(text=tb, embed=embed)
        logger.info("Bluesky post success")

    except Exception as e:
        logger.error(f"Error posting to Bluesky: {e}")
        raise


def post_to_mastodon(text: str, img_path: Optional[str], alt_text: str) -> None:
    """Post plain text status with optional media to Mastodon."""
    token = os.getenv('MASTO_TOKEN')

    if not token:
        raise AuthenticationError("MASTO_TOKEN environment variable not set")

    try:
        mastodon = Mastodon(
            access_token=token,
            api_base_url=MASTODON_INSTANCE
        )

        media_ids = []
        if img_path and os.path.exists(img_path):
            try:
                media = mastodon.media_post(img_path, description=alt_text or "")
                media_ids.append(media['id'])
            except Exception as e:
                logger.error(f"Error uploading image to Mastodon: {e}")
                # Continue without image

        mastodon.status_post(
            status=text[:500],
            media_ids=media_ids if media_ids else None
        )
        logger.info("Mastodon post success")

    except Exception as e:
        logger.error(f"Error posting to Mastodon: {e}")
        raise


def validate_config(config: List[Dict[str, Any]]) -> None:
    """Validate configuration structure and required fields."""
    required_fields = ['url', 'template', 'targets']

    for i, cfg in enumerate(config):
        for field in required_fields:
            if field not in cfg:
                raise ConfigurationError(
                    f"Config entry {i} missing required field: {field}"
                )

        if not isinstance(cfg['targets'], list):
            raise ConfigurationError(
                f"Config entry {i}: 'targets' must be a list"
            )

        valid_targets = {PLATFORM_BLUESKY, PLATFORM_MASTODON}
        for target in cfg['targets']:
            if target not in valid_targets:
                raise ConfigurationError(
                    f"Config entry {i}: invalid target '{target}'. "
                    f"Must be one of {valid_targets}"
                )


def validate_credentials(config: List[Dict[str, Any]]) -> None:
    """Validate that required credentials are present for configured platforms."""
    required_platforms = set()

    for cfg in config:
        required_platforms.update(cfg.get('targets', []))

    if PLATFORM_BLUESKY in required_platforms:
        if not os.getenv('BSKY_HANDLE') or not os.getenv('BSKY_PW'):
            raise AuthenticationError(
                "Bluesky credentials missing: BSKY_HANDLE and BSKY_PW required"
            )

    if PLATFORM_MASTODON in required_platforms:
        if not os.getenv('MASTO_TOKEN'):
            raise AuthenticationError(
                "Mastodon credentials missing: MASTO_TOKEN required"
            )


def process_entry(
    entry: Any,
    cfg: Dict[str, Any],
    posted_cache: Set[str]
) -> bool:
    """
    Process a single feed entry.
    Returns True if successfully posted, False otherwise.
    """
    if is_posted(entry.link, posted_cache):
        return False

    # --- PRECISE FILTERING (Title, Text-Hashtags & RSS-Categories only) ---
    content_html = (
        entry.content[0].value if hasattr(entry, 'content')
        else entry.get('summary', '')
    )

    # Extract hashtags from text content
    found_hashtags = " ".join(re.findall(r'#\w+', content_html))

    # Extract categories (tags) provided by the Bear Blog RSS feed
    rss_categories = ""
    if hasattr(entry, 'tags'):
        rss_categories = " ".join([
            tag.term for tag in entry.tags if hasattr(tag, 'term')
        ])

    # Combine metadata for inclusion/exclusion checks
    check_string = (
        entry.title + " " + found_hashtags + " " + rss_categories
    ).lower()

    # Apply filters
    if any(w.lower() in check_string for w in cfg.get('exclude', [])):
        logger.debug(f"Skipping (excluded): {entry.title}")
        return False

    if cfg.get('include') and not any(
        w.lower() in check_string for w in cfg['include']
    ):
        logger.debug(f"Skipping (not included): {entry.title}")
        return False

    logger.info(f"Processing: {entry.title}")

    # Extract image if needed
    img_data = None
    img_path = None
    alt_text = ""

    if cfg.get('include_images'):
        img_data = get_first_image_data(entry)
        if img_data:
            img_path = download_image(img_data['url'])
            alt_text = img_data.get('alt', '')

    clean_content = get_html_content(entry)

    # Format message using the template from config.json
    msg = cfg['template'].format(
        title=entry.title,
        link=entry.link,
        content=clean_content
    )

    try:
        # Post to configured platforms
        if PLATFORM_BLUESKY in cfg.get('targets', []):
            post_to_bluesky(msg, img_path, alt_text, link=entry.link)

        if PLATFORM_MASTODON in cfg.get('targets', []):
            post_to_mastodon(msg, img_path, alt_text)

        # Submit to search engines
        submit_to_indexnow(entry.link)

        # Mark as posted
        mark_as_posted(entry.link)
        posted_cache.add(entry.link)  # Update in-memory cache

        return True

    except Exception as e:
        logger.error(f"Error processing entry '{entry.title}': {e}")
        return False

    finally:
        # Clean up temporary image file
        if img_path and os.path.exists(img_path):
            try:
                os.unlink(img_path)
            except Exception as e:
                logger.warning(f"Error removing temporary file {img_path}: {e}")


def run() -> None:
    """Main execution logic to parse feeds and post new entries based on configuration."""
    logger.info("=== Social Bot Start ===")

    try:
        # Load and validate configuration
        if not CONFIG_FILE.exists():
            raise ConfigurationError(f"Config file not found: {CONFIG_FILE}")

        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)

        validate_config(config)
        validate_credentials(config)

        # Load posted articles cache
        posted_cache = load_posted_articles()
        logger.info(f"Loaded {len(posted_cache)} previously posted articles")

        # Load feed cache for ETag/Last-Modified tracking
        feed_cache = load_feed_cache()
        cache_updated = False

        # Process feeds
        total_processed = 0
        total_entries = 0
        feeds_checked = 0
        feeds_skipped = 0

        for cfg in config:
            try:
                feed_url = cfg['url']
                feeds_checked += 1

                # Check if feed has changed using HEAD request
                has_changed, new_headers = check_feed_changed(feed_url, feed_cache)

                if not has_changed:
                    logger.info(f"Skipping unchanged feed: {feed_url}")
                    feeds_skipped += 1
                    continue

                # Feed has changed, fetch full content
                logger.info(f"Fetching feed: {feed_url}")
                response = session.get(feed_url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()

                feed = feedparser.parse(response.content)

                if feed.bozo:
                    logger.warning(f"Feed parsing warning for {feed_url}: {feed.bozo_exception}")

                logger.info(f"Found {len(feed.entries)} entries in feed")
                total_entries += len(feed.entries)

                for entry in feed.entries:
                    if process_entry(entry, cfg, posted_cache):
                        total_processed += 1

                # Update cache with new headers after successful fetch
                if new_headers:
                    feed_cache[feed_url] = new_headers
                    cache_updated = True

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching feed {cfg['url']}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error processing feed {cfg['url']}: {e}")
                continue

        # Save updated cache
        if cache_updated:
            save_feed_cache(feed_cache)
            logger.info("Feed cache updated")

        logger.info(f"=== Social Bot End === (Checked {feeds_checked} feeds, skipped {feeds_skipped} unchanged, processed {total_processed}/{total_entries} entries)")

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except AuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in main execution: {e}")
        raise


if __name__ == "__main__":
    run()
