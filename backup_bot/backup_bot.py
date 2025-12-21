"""
Bear Blog backup automation with GitHub integration.
Includes security hardening, performance optimizations, and improved error handling.
"""

import pandas as pd
import requests
import os
import re
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import yaml

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- CONSTANTS ---
CSV_URL = "https://bearblog.dev/fischr/dashboard/settings/?export=true"
REQUEST_TIMEOUT = 15
MAX_IMAGE_SIZE = 10_000_000  # 10MB limit
MAX_CSV_SIZE = 50_000_000  # 50MB limit for CSV
MAX_WORKERS = 5  # Concurrent image downloads

# Security: Allowed image domains
ALLOWED_IMAGE_DOMAINS = {
    'bearblog.dev',
    'digitaloceanspaces.com',  # Bear Blog CDN (bear-images.sfo2.cdn.digitaloceanspaces.com)
    'imgur.com',
    'i.imgur.com',
    'cloudinary.com',
    'githubusercontent.com',
    'fischr.org'
}

# Paths
BASE_DIR = Path("blog_posts")
TRACKING_FILE = Path("backup_bot/processed_articles.txt")
TEMP_CSV = Path("temp_export.csv")
DEBUG_CSV = Path("backup_bot/last_export.csv")  # Keep a copy for debugging

# Environment variables
def normalize_cookie(cookie: Optional[str]) -> Optional[str]:
    """
    Normalize cookie format to ensure it has the sessionid= prefix.
    Accepts both formats:
    - sessionid=VALUE (already formatted)
    - VALUE (just the session ID value)
    """
    if not cookie:
        return None

    cookie = cookie.strip()

    # If it already starts with sessionid=, return as is
    if cookie.startswith('sessionid='):
        return cookie

    # Otherwise, add the sessionid= prefix
    return f'sessionid={cookie}'

COOKIE = normalize_cookie(os.getenv("BEAR_COOKIE"))


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class DownloadError(Exception):
    """Raised when download fails."""
    pass


def clean_filename(text: str) -> str:
    """
    Creates a safe filename for files and folders.
    Removes special characters and emojis.
    """
    # Remove emojis and special characters
    text = re.sub(r'[^\w\s-]', '', str(text)).strip().lower()
    # Replace spaces and multiple hyphens with single hyphen
    text = re.sub(r'[-\s]+', '-', text)
    # Limit length
    return text[:100]


def is_safe_url(url: str) -> bool:
    """Validate that the URL is from an allowed domain and uses safe protocol."""
    try:
        parsed = urlparse(url)

        # Only allow HTTP/HTTPS
        if parsed.scheme not in ('http', 'https'):
            logger.warning(f"Rejected URL with unsafe protocol: {parsed.scheme}")
            return False

        domain = parsed.netloc.lower().replace('www.', '')

        # Check if domain is in whitelist
        for allowed in ALLOWED_IMAGE_DOMAINS:
            if domain == allowed or domain.endswith('.' + allowed):
                return True

        logger.warning(f"Rejected URL from untrusted domain: {domain}")
        return False

    except Exception as e:
        logger.warning(f"Error validating URL: {e}")
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.
    Returns only the basename without any directory components.
    """
    # Remove any path components
    filename = os.path.basename(filename)

    # Remove dangerous characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

    # Prevent hidden files
    if filename.startswith('.'):
        filename = '_' + filename

    # Ensure filename is not empty and has reasonable length
    if not filename or len(filename) > 255:
        filename = 'image.webp'

    return filename


def download_file(url: str, folder: Path) -> bool:
    """
    Downloads a file without changing URLs in the markdown.
    Includes security checks and proper error handling.
    """
    try:
        # Security: Validate URL
        if not is_safe_url(url):
            logger.warning(f"Skipping unsafe URL: {url}")
            return False

        # Extract and sanitize filename
        url_path = urlparse(url).path
        file_name = url_path.split("/")[-1].split("?")[0]

        if not file_name:
            file_name = "image.webp"

        file_name = sanitize_filename(file_name)
        path = folder / file_name

        logger.info(f"Downloading image: {file_name}")

        # Download with streaming and size limit
        response = requests.get(url, stream=True, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        # Check content length
        content_length = int(response.headers.get('content-length', 0))
        if content_length > MAX_IMAGE_SIZE:
            logger.warning(f"Image too large ({content_length} bytes): {url}")
            return False

        # Download with size check
        total_size = 0
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                total_size += len(chunk)
                if total_size > MAX_IMAGE_SIZE:
                    logger.warning(f"Image download exceeded size limit: {url}")
                    path.unlink()
                    return False
                f.write(chunk)

        logger.info(f"Successfully downloaded: {file_name}")
        return True

    except requests.exceptions.RequestException as e:
        logger.warning(f"HTTP error downloading {url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {e}")
        return False


def get_content_hash(row: pd.Series) -> str:
    """
    Creates a secure hash from content AND relevant metadata to detect changes.
    This ensures that changes to meta_image, title, etc. trigger re-processing.
    """
    # Include content and all metadata that should trigger a re-download
    hash_parts = [
        str(row.get('content', '')),
        str(row.get('meta image', '')),
        str(row.get('title', '')),
        str(row.get('meta description', '')),
        str(row.get('canonical url', '')),
    ]
    combined = '|'.join(hash_parts)
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def load_processed_articles() -> Dict[str, str]:
    """Loads the list of already processed articles (UID + Hash)."""
    processed = {}

    if not TRACKING_FILE.exists():
        return processed

    try:
        with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                if '|' not in line:
                    logger.warning(f"Invalid format in tracking file at line {line_num}")
                    continue

                parts = line.split('|', 1)
                if len(parts) == 2:
                    uid, content_hash = parts
                    processed[uid] = content_hash

        return processed

    except Exception as e:
        logger.error(f"Error loading processed articles: {e}")
        return {}


def save_processed_article(uid: str, content_hash: str) -> None:
    """Saves a processed article to the tracking file."""
    try:
        TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TRACKING_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{uid}|{content_hash}\n")
    except Exception as e:
        logger.error(f"Error saving processed article: {e}")
        raise


def update_processed_article(uid: str, content_hash: str) -> None:
    """Updates an existing entry in the tracking file."""
    try:
        processed = load_processed_articles()
        processed[uid] = content_hash

        TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
            for article_uid, hash_val in processed.items():
                f.write(f"{article_uid}|{hash_val}\n")

    except Exception as e:
        logger.error(f"Error updating processed article: {e}")
        raise


def safe_yaml_string(value: str) -> str:
    """
    Safely escape a string for YAML frontmatter.
    Handles multiline strings, special characters, and YAML syntax.
    """
    if not value or value == 'nan':
        return '""'

    # Convert to string and strip
    value = str(value).strip()

    # Check if value needs quoting (contains special chars or is multiline)
    needs_quoting = any(c in value for c in [':', '#', '[', ']', '{', '}', '\n', '"', "'"])

    if '\n' in value:
        # Use literal block scalar for multiline
        lines = value.split('\n')
        return '|\n  ' + '\n  '.join(lines)
    elif needs_quoting or value.lower() in ('true', 'false', 'null', 'yes', 'no'):
        # Escape and quote
        value = value.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{value}"'
    else:
        return value


def download_images_concurrent(content: str, post_dir: Path) -> None:
    """
    Download all images from content concurrently for better performance.
    Extracts URLs from both Markdown and HTML formats.
    Only downloads from <img> tags, NOT from <iframe> or other elements.
    """
    # Find all image URLs (Markdown ![]() and HTML <img src="">)
    img_urls = set()

    # Markdown format: ![alt](url)
    markdown_imgs = re.findall(r'!\[.*?\]\((https?://[^\)]+)\)', content)
    img_urls.update(markdown_imgs)

    # HTML format: <img src="url"> - specifically target img tags only
    html_imgs = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
    img_urls.update(html_imgs)

    if not img_urls:
        return

    logger.info(f"Found {len(img_urls)} images to download")

    # Download concurrently
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {
            executor.submit(download_file, url, post_dir): url
            for url in img_urls
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error in concurrent download of {url}: {e}")


def download_csv() -> Path:
    """
    Download CSV from Bear Blog with authentication.
    Returns path to downloaded CSV file.
    """
    if not COOKIE:
        raise AuthenticationError(
            "BEAR_COOKIE environment variable not set. "
            "Please add your sessionid cookie as a GitHub Secret."
        )

    logger.info(f"Fetching CSV from: {CSV_URL}")
    logger.debug(f"Cookie format: {'sessionid=***' if COOKIE.startswith('sessionid=') else 'Missing sessionid= prefix'}")

    headers = {"Cookie": COOKIE}

    try:
        response = requests.get(
            CSV_URL,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
            stream=True
        )

        # Check for authentication issues
        if response.status_code == 403:
            raise AuthenticationError(
                "Authentication failed (403 Forbidden). "
                "Your Bear Blog session cookie has expired. "
                "Please update the BEAR_COOKIE secret."
            )

        if response.status_code in (301, 302):
            raise AuthenticationError(
                "Redirect detected (login required). "
                "Your session cookie is no longer valid. "
                "Please update the BEAR_COOKIE secret."
            )

        if response.status_code != 200:
            raise DownloadError(
                f"HTTP {response.status_code} error when downloading CSV"
            )

        # Check size limit from header
        content_length = int(response.headers.get('content-length', 0))
        if content_length > MAX_CSV_SIZE:
            raise DownloadError(
                f"CSV file too large: {content_length} bytes (max: {MAX_CSV_SIZE})"
            )

        # Download using a single iterator to avoid stream issues
        # Collect all chunks first, then validate and write
        chunks = []
        total_size = 0
        html_checked = False

        for chunk in response.iter_content(chunk_size=8192):
            # Check first chunk for HTML (login page detection)
            if not html_checked:
                if b'<!doctype' in chunk.lower() or b'<html' in chunk.lower():
                    raise AuthenticationError(
                        "Received HTML instead of CSV (likely login page). "
                        "Your session cookie is invalid or expired. "
                        "Please update the BEAR_COOKIE secret."
                    )
                html_checked = True

            total_size += len(chunk)
            if total_size > MAX_CSV_SIZE:
                raise DownloadError("CSV download exceeded size limit")
            chunks.append(chunk)

        # Write all chunks to file
        content = b''.join(chunks)
        with open(TEMP_CSV, 'wb') as f:
            f.write(content)

        # Also save a debug copy that will be committed to the repo
        DEBUG_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(DEBUG_CSV, 'wb') as f:
            f.write(content)
        logger.info(f"Debug copy saved to: {DEBUG_CSV}")

        # Validate minimum size
        if total_size < 100:
            TEMP_CSV.unlink()
            raise DownloadError(
                f"Downloaded CSV too small ({total_size} bytes). "
                "This may indicate an authentication or server error."
            )

        logger.info(f"CSV downloaded successfully ({total_size} bytes)")
        return TEMP_CSV

    except requests.exceptions.RequestException as e:
        raise DownloadError(f"Network error downloading CSV: {e}")


def parse_csv(csv_path: Path) -> pd.DataFrame:
    """Parse CSV file with robust error handling."""
    try:
        # First, check if file is empty or too small
        file_size = csv_path.stat().st_size
        if file_size == 0:
            raise ValueError("CSV file is empty (0 bytes)")
        if file_size < 100:
            raise ValueError(f"CSV file suspiciously small ({file_size} bytes)")

        # Use C engine which handles multiline quoted fields correctly
        # The Python engine has issues with multiline content in quoted fields
        df = pd.read_csv(
            csv_path,
            encoding='utf-8-sig',  # Remove BOM (Byte Order Mark) if present
            engine='c',  # C engine handles multiline quoted fields better
            sep=',',  # BearBlog uses comma-separated CSV
            quotechar='"',  # Standard quote character
            doublequote=True,  # Handle double quotes
            skipinitialspace=True,  # Skip spaces after delimiter
            on_bad_lines='warn'  # Warn about bad lines instead of failing
        )

        logger.info(f"Parsed CSV: {len(df)} articles found")
        logger.info(f"Columns: {list(df.columns)}")

        # Validate required columns
        required_columns = ['uid', 'title', 'content', 'published date', 'slug', 'publish']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise ValueError(f"CSV missing required columns: {missing_columns}")

        # Check if DataFrame is empty
        if len(df) == 0:
            raise ValueError("CSV file contains no data rows")

        return df

    except Exception as e:
        logger.error(f"Error parsing CSV: {e}")

        # Debug output
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                logger.info("First 5 lines of CSV for debugging:")
                for i, line in enumerate(f):
                    if i < 5:
                        logger.info(f"Line {i+1}: {line[:100]}...")
        except Exception as debug_e:
            logger.error(f"Could not read CSV for debugging: {debug_e}")

        raise


def process_article(row: pd.Series, df: pd.DataFrame, processed_articles: Dict[str, str]) -> Tuple[str, int]:
    """
    Process a single article from the CSV.
    Returns tuple of (status, change_type) where:
    - status: 'new', 'updated', 'skipped', or 'error'
    - change_type: 0=skipped, 1=new, 2=updated, -1=error
    """
    try:
        # Only process published articles
        if str(row.get('publish', '')).lower() != 'true':
            return ('skipped', 0)

        # Extract data
        uid = str(row['uid'])
        title = str(row['title'])
        content = str(row['content'])
        pub_date_str = str(row['published date'])
        slug = str(row['slug'])

        # Calculate content hash (includes content + metadata)
        content_hash = get_content_hash(row)

        # Check if article was already processed
        if uid in processed_articles:
            if processed_articles[uid] == content_hash:
                # Article unchanged - skip
                return ('skipped', 0)
            else:
                # Article changed - reprocess
                logger.info(f"UPDATE: {slug} (content changed)")
                status = 'updated'
                change_type = 2
        else:
            logger.info(f"NEW: {slug}")
            status = 'new'
            change_type = 1

        # Format date for folder name
        try:
            dt = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
            date_prefix = dt.strftime("%Y-%m-%d")
        except Exception as e:
            logger.warning(f"Error parsing date '{pub_date_str}': {e}")
            date_prefix = "0000-00-00"

        # Create folder: YYYY-MM-DD-title
        folder_name = f"{date_prefix}-{clean_filename(slug)}"
        post_dir = BASE_DIR / folder_name
        post_dir.mkdir(parents=True, exist_ok=True)

        # Download images concurrently (from content)
        download_images_concurrent(content, post_dir)

        # Create index.md with proper YAML frontmatter
        with open(post_dir / "index.md", "w", encoding="utf-8") as f:
            f.write("---\n")

            # Add all columns from CSV dynamically to frontmatter
            for col in df.columns:
                if col != 'content':  # Content goes below frontmatter
                    val = str(row[col])
                    safe_val = safe_yaml_string(val)
                    col_name = col.replace(' ', '_')
                    f.write(f"{col_name}: {safe_val}\n")

            f.write("---\n\n")
            f.write(content)

        # Update tracking
        if status == 'updated':
            update_processed_article(uid, content_hash)
        else:
            save_processed_article(uid, content_hash)

        logger.info(f"Successfully processed: {folder_name}")
        return (status, change_type)

    except Exception as e:
        logger.error(f"Error processing article: {e}")
        return ('error', -1)


def cleanup_temp_files() -> None:
    """Clean up temporary files."""
    try:
        if TEMP_CSV.exists():
            TEMP_CSV.unlink()
            logger.debug("Cleaned up temporary CSV file")
    except Exception as e:
        logger.warning(f"Error cleaning up temp files: {e}")


def main() -> None:
    """Main execution logic."""
    logger.info("=" * 70)
    logger.info("Bear Blog Backup to GitHub - Starting")
    logger.info("=" * 70)

    try:
        # Download CSV
        csv_path = download_csv()

        # Parse CSV
        df = parse_csv(csv_path)

        # Load tracking
        processed_articles = load_processed_articles()
        logger.info(f"Already processed: {len(processed_articles)} articles")

        # Statistics
        stats = {
            'new': 0,
            'updated': 0,
            'skipped': 0,
            'error': 0
        }

        # Process all articles
        total = len(df)
        for idx, row in df.iterrows():
            status, change_type = process_article(row, df, processed_articles)
            stats[status] += 1

            # Progress indicator
            if (idx + 1) % 10 == 0:
                logger.info(f"Progress: {idx + 1}/{total} articles processed")

        # Summary
        logger.info("=" * 70)
        logger.info("Backup Complete!")
        logger.info(f"  New articles: {stats['new']}")
        logger.info(f"  Updated articles: {stats['updated']}")
        logger.info(f"  Skipped (unchanged/unpublished): {stats['skipped']}")
        logger.info(f"  Errors: {stats['error']}")
        logger.info("=" * 70)

        # Cleanup
        cleanup_temp_files()

    except AuthenticationError as e:
        logger.error("=" * 70)
        logger.error("AUTHENTICATION ERROR")
        logger.error("=" * 70)
        logger.error(str(e))
        logger.error("")
        logger.error("To fix this:")
        logger.error("  1. Go to https://bearblog.dev/fischr/dashboard/")
        logger.error("  2. Press F12 -> Application/Storage -> Cookies")
        logger.error("  3. Copy the value of 'sessionid'")
        logger.error("  4. Update the GitHub Secret 'BEAR_COOKIE':")
        logger.error("     - Go to: Settings -> Secrets and variables -> Actions")
        logger.error("     - Edit 'BEAR_COOKIE'")
        logger.error("     - Value: Just paste the sessionid value")
        logger.error("     - (You can use either 'sessionid=VALUE' or just 'VALUE')")
        logger.error("=" * 70)
        # Note: Don't cleanup - we want to keep the debug CSV for inspection
        raise

    except DownloadError as e:
        logger.error(f"Download error: {e}")
        # Note: Don't cleanup - we want to keep the debug CSV for inspection
        raise

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        # Note: Don't cleanup - we want to keep the debug CSV for inspection
        raise


if __name__ == "__main__":
    main()
