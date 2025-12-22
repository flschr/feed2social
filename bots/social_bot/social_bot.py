"""
Social media bot for automating posts from RSS feeds to Bluesky and Mastodon.
"""

import feedparser
import json
import os
import re
import logging
import tempfile
from typing import Optional, Dict, List, Set, Any
from pathlib import Path
from bs4 import BeautifulSoup
from atproto import Client, client_utils, models
from mastodon import Mastodon

# Import shared utilities
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared import (
    CONFIG,
    AuthenticationError,
    ConfigurationError,
    REQUEST_TIMEOUT,
    MAX_IMAGE_SIZE,
    is_safe_url,
    create_session,
    FileLock,
)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- CONFIG ---
MASTODON_INSTANCE = CONFIG['social']['mastodon_instance']

# --- CONSTANTS ---
PLATFORM_BLUESKY = "bluesky"
PLATFORM_MASTODON = "mastodon"

BASE_DIR = Path(__file__).parent.absolute()
POSTED_FILE = BASE_DIR / 'posted_articles.txt'
LOCK_FILE = BASE_DIR / 'posted_articles.txt.lock'
CONFIG_FILE = BASE_DIR / 'config.json'
FEED_CACHE_FILE = BASE_DIR / 'feed_cache.json'

# Create session with connection pooling
session = create_session('feed2social/2.0')


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
        response = session.head(feed_url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        response.raise_for_status()

        new_headers = {
            'etag': response.headers.get('ETag', ''),
            'last-modified': response.headers.get('Last-Modified', '')
        }

        if feed_url not in cache:
            logger.info(f"No cache for {feed_url}, will fetch")
            return True, new_headers

        cached_headers = cache[feed_url]

        if new_headers['etag'] and cached_headers.get('etag'):
            if new_headers['etag'] == cached_headers['etag']:
                logger.info(f"Feed unchanged (ETag match): {feed_url}")
                return False, new_headers

        if new_headers['last-modified'] and cached_headers.get('last-modified'):
            if new_headers['last-modified'] == cached_headers['last-modified']:
                logger.info(f"Feed unchanged (Last-Modified match): {feed_url}")
                return False, new_headers

        logger.info(f"Feed changed or no cache headers: {feed_url}")
        return True, new_headers

    except Exception as e:
        logger.warning(f"Error checking feed headers for {feed_url}: {e}")
        return True, {}


def load_posted_articles() -> Set[str]:
    """
    Load all posted article URLs into memory for fast lookup.
    Returns a set for O(1) lookup time.
    """
    if not POSTED_FILE.exists():
        return set()

    try:
        with FileLock(LOCK_FILE):
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
        with FileLock(LOCK_FILE):
            existing_lines = []
            if POSTED_FILE.exists():
                with open(POSTED_FILE, 'r', encoding='utf-8') as f:
                    existing_lines = f.readlines()

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

        for img in soup.find_all('img'):
            img.decompose()

        text = soup.get_text(separator=' ')
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    except Exception as e:
        logger.warning(f"Error extracting HTML content: {e}")
        return ""


def get_first_image_data(entry: Any) -> Optional[Dict[str, str]]:
    """Extract the first image URL and its alt text from the post."""
    try:
        html = entry.content[0].value if hasattr(entry, 'content') else entry.get('summary', '')
        soup = BeautifulSoup(html, "html.parser")
        img = soup.find('img')

        if img and img.get('src'):
            img_url = img.get('src')

            if not is_safe_url(img_url):
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
    """
    try:
        if not is_safe_url(img_url):
            logger.warning(f"Rejected unsafe image URL: {img_url}")
            return None

        temp_file = tempfile.NamedTemporaryFile(
            mode='wb',
            suffix='.jpg',
            delete=False,
            dir=BASE_DIR
        )

        try:
            r = session.get(img_url, timeout=REQUEST_TIMEOUT, stream=True)
            r.raise_for_status()

            content_length = int(r.headers.get('content-length', 0))
            if content_length > MAX_IMAGE_SIZE:
                logger.warning(f"Image too large: {content_length} bytes")
                temp_file.close()
                os.unlink(temp_file.name)
                return None

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

    except Exception as e:
        logger.warning(f"Error downloading image from {img_url}: {e}")
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
    except Exception as e:
        logger.warning(f"Error fetching OG metadata from {url}: {e}")
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
    except Exception as e:
        logger.warning(f"IndexNow request failed: {e}")


def post_to_bluesky(text: str, img_path: Optional[str], alt_text: str, link: Optional[str] = None) -> None:
    """Post rich text to Bluesky with link card preview."""
    handle = os.getenv('BSKY_HANDLE')
    password = os.getenv('BSKY_PW')

    if not handle or not password:
        raise AuthenticationError("BSKY_HANDLE or BSKY_PW environment variables not set")

    try:
        client = Client()
        client.login(handle, password)

        tb = client_utils.TextBuilder()

        words = text.split(' ')
        for i, word in enumerate(words):
            if word.startswith('#') and len(word) > 1:
                tag_name = word[1:].rstrip('.,!?')
                tb.tag(word, tag_name)
            elif word.startswith('http'):
                tb.link(word, word)
            else:
                tb.text(word)

            if i < len(words) - 1:
                tb.text(' ')

        embed = None

        if link:
            try:
                og_data = get_og_metadata(link)
                if og_data:
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
                                if og_img_path and os.path.exists(og_img_path):
                                    try:
                                        os.unlink(og_img_path)
                                    except Exception as e:
                                        logger.warning(f"Error removing OG image file: {e}")

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

    content_html = (
        entry.content[0].value if hasattr(entry, 'content')
        else entry.get('summary', '')
    )

    found_hashtags = " ".join(re.findall(r'#\w+', content_html))

    rss_categories = ""
    if hasattr(entry, 'tags'):
        rss_categories = " ".join([
            tag.term for tag in entry.tags if hasattr(tag, 'term')
        ])

    check_string = (
        entry.title + " " + found_hashtags + " " + rss_categories
    ).lower()

    if any(w.lower() in check_string for w in cfg.get('exclude', [])):
        logger.debug(f"Skipping (excluded): {entry.title}")
        return False

    if cfg.get('include') and not any(
        w.lower() in check_string for w in cfg['include']
    ):
        logger.debug(f"Skipping (not included): {entry.title}")
        return False

    logger.info(f"Processing: {entry.title}")

    img_data = None
    img_path = None
    alt_text = ""

    if cfg.get('include_images'):
        img_data = get_first_image_data(entry)
        if img_data:
            img_path = download_image(img_data['url'])
            alt_text = img_data.get('alt', '')

    clean_content = get_html_content(entry)

    msg = cfg['template'].format(
        title=entry.title,
        link=entry.link,
        content=clean_content
    )

    try:
        if PLATFORM_BLUESKY in cfg.get('targets', []):
            post_to_bluesky(msg, img_path, alt_text, link=entry.link)

        if PLATFORM_MASTODON in cfg.get('targets', []):
            post_to_mastodon(msg, img_path, alt_text)

        submit_to_indexnow(entry.link)

        mark_as_posted(entry.link)
        posted_cache.add(entry.link)

        return True

    except Exception as e:
        logger.error(f"Error processing entry '{entry.title}': {e}")
        return False

    finally:
        if img_path and os.path.exists(img_path):
            try:
                os.unlink(img_path)
            except Exception as e:
                logger.warning(f"Error removing temporary file {img_path}: {e}")


def run() -> None:
    """Main execution logic to parse feeds and post new entries based on configuration."""
    logger.info("=== Social Bot Start ===")

    try:
        if not CONFIG_FILE.exists():
            raise ConfigurationError(f"Config file not found: {CONFIG_FILE}")

        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)

        validate_config(config)
        validate_credentials(config)

        posted_cache = load_posted_articles()
        logger.info(f"Loaded {len(posted_cache)} previously posted articles")

        feed_cache = load_feed_cache()
        cache_updated = False

        total_processed = 0
        total_entries = 0
        feeds_checked = 0
        feeds_skipped = 0

        for cfg in config:
            try:
                feed_url = cfg['url']
                feeds_checked += 1

                has_changed, new_headers = check_feed_changed(feed_url, feed_cache)

                if not has_changed:
                    logger.info(f"Skipping unchanged feed: {feed_url}")
                    feeds_skipped += 1
                    continue

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

                if new_headers:
                    feed_cache[feed_url] = new_headers
                    cache_updated = True

            except Exception as e:
                logger.error(f"Error processing feed {cfg['url']}: {e}")
                continue

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
