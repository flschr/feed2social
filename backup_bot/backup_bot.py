import pandas as pd
import requests
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime

# Configuration
CSV_URL = "https://bearblog.dev/fischr/dashboard/settings/?export=true"
COOKIE = os.getenv("BEAR_COOKIE")
BASE_DIR = Path("blog_posts")
TRACKING_FILE = Path("backup_bot/processed_articles.txt")  # Tracking for already processed articles

def clean_filename(text):
    """Creates a safe filename for files and folders."""
    # Removes emojis and special characters, keeps only alphanumeric, spaces, and hyphens
    text = re.sub(r'[^\w\s-]', '', str(text)).strip().lower()
    return re.sub(r'[-\s]+', '-', text)

def download_file(url, folder):
    """Downloads a file without changing URLs in the markdown."""
    try:
        # Extract filename from URL
        file_name = url.split("/")[-1].split("?")[0]
        if not file_name:
            file_name = "image.webp"

        path = folder / file_name
        if not path.exists():
            print(f"  📥 Downloading image: {file_name}", flush=True)
            r = requests.get(url, stream=True, timeout=10)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    for chunk in r:
                        f.write(chunk)
                return True
            else:
                print(f"  ⚠️  HTTP {r.status_code} for {url}", flush=True)
                return False
        else:
            print(f"  ✓ Image already exists: {file_name}", flush=True)
            return True
    except Exception as e:
        print(f"  ❌ Error downloading {url}: {e}", flush=True)
        return False

def get_content_hash(content):
    """Creates a hash from content to detect changes."""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def load_processed_articles():
    """Loads the list of already processed articles (UID + Hash)."""
    processed = {}
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '|' in line:
                    uid, content_hash = line.split('|', 1)
                    processed[uid] = content_hash
    return processed

def save_processed_article(uid, content_hash):
    """Saves a processed article to the tracking file."""
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKING_FILE, 'a') as f:
        f.write(f"{uid}|{content_hash}\n")

def update_processed_article(uid, content_hash):
    """Updates an existing entry in the tracking file."""
    processed = load_processed_articles()
    processed[uid] = content_hash

    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKING_FILE, 'w') as f:
        for uid, h in processed.items():
            f.write(f"{uid}|{h}\n")

def main():
    print("🚀 Starting Bear Blog Backup to GitHub...\n", flush=True)

    # Load CSV
    if not COOKIE:
        print("❌ ERROR: BEAR_COOKIE environment variable not set!", flush=True)
        print("Please add your sessionid cookie as a GitHub Secret.", flush=True)
        return

    print(f"📡 Fetching CSV from: {CSV_URL}", flush=True)
    headers = {"Cookie": COOKIE}

    try:
        response = requests.get(CSV_URL, headers=headers, timeout=15, allow_redirects=False)

        if response.status_code == 403:
            print("\n" + "=" * 70, flush=True)
            print("❌ ERROR: AUTHENTICATION FAILED (403 Forbidden)", flush=True)
            print("=" * 70, flush=True)
            print("", flush=True)
            print("🔑 Your Bear Blog session cookie has expired!", flush=True)
            print("", flush=True)
            print("To fix this:", flush=True)
            print("  1. Go to https://bearblog.dev/fischr/dashboard/", flush=True)
            print("  2. Press F12 → Application/Storage → Cookies", flush=True)
            print("  3. Copy the value of 'sessionid'", flush=True)
            print("  4. Update the GitHub Secret 'BEAR_COOKIE':", flush=True)
            print("     - Go to: Settings → Secrets and variables → Actions", flush=True)
            print("     - Edit 'BEAR_COOKIE'", flush=True)
            print("     - Value: sessionid=YOUR_NEW_VALUE", flush=True)
            print("", flush=True)
            print("=" * 70, flush=True)
            return
        elif response.status_code == 302 or response.status_code == 301:
            print("\n" + "=" * 70, flush=True)
            print("❌ ERROR: REDIRECT DETECTED (Login Required)", flush=True)
            print("=" * 70, flush=True)
            print("", flush=True)
            print("🔑 You are being redirected to the login page!", flush=True)
            print("   This means your session cookie is no longer valid.", flush=True)
            print("", flush=True)
            print("Please update your BEAR_COOKIE as described above.", flush=True)
            print("=" * 70, flush=True)
            return
        elif response.status_code != 200:
            print(f"\n❌ ERROR: HTTP {response.status_code}", flush=True)
            print(f"Response: {response.text[:200]}", flush=True)
            return

        # Check if we got HTML instead of CSV (login page)
        content_type = response.headers.get('Content-Type', '')
        response_preview = response.text[:200].lower()

        if 'html' in content_type or '<!doctype' in response_preview or '<html' in response_preview:
            print("\n" + "=" * 70, flush=True)
            print("❌ ERROR: RECEIVED HTML INSTEAD OF CSV", flush=True)
            print("=" * 70, flush=True)
            print("", flush=True)
            print("🔑 The server returned an HTML page (likely login) instead of CSV!", flush=True)
            print("   Your session cookie is invalid or expired.", flush=True)
            print("", flush=True)
            print(f"Content-Type received: {content_type}", flush=True)
            print(f"Response preview: {response.text[:300]}", flush=True)
            print("", flush=True)
            print("To fix this:", flush=True)
            print("  1. Go to https://bearblog.dev/fischr/dashboard/", flush=True)
            print("  2. Press F12 → Application/Storage → Cookies", flush=True)
            print("  3. Copy the FULL value of 'sessionid'", flush=True)
            print("  4. Update the GitHub Secret 'BEAR_COOKIE':", flush=True)
            print("     - Go to: Settings → Secrets and variables → Actions", flush=True)
            print("     - Edit 'BEAR_COOKIE'", flush=True)
            print("     - Value: sessionid=YOUR_NEW_SESSION_ID", flush=True)
            print("", flush=True)
            print("=" * 70, flush=True)
            return

        with open("temp_export.csv", "wb") as f:
            f.write(response.content)

        print("✓ CSV downloaded successfully\n", flush=True)

    except Exception as e:
        print(f"❌ Error fetching CSV: {e}", flush=True)
        return

    # Process CSV with robust parsing options
    try:
        df = pd.read_csv(
            "temp_export.csv",
            encoding='utf-8',
            sep=None,  # Auto-detect delimiter
            on_bad_lines='warn',  # Warn about bad lines instead of failing
            engine='python',  # Use Python engine for more flexible parsing
            quoting=1,  # QUOTE_ALL - expect all fields to be quoted
            escapechar='\\',  # Handle escaped characters
            doublequote=True  # Handle double quotes
        )

        # Debug output to show CSV structure
        print(f"📊 Found {len(df)} articles in CSV", flush=True)
        print(f"📋 Columns found: {list(df.columns)}", flush=True)
        print(f"🔍 Sample row (first article):", flush=True)
        if len(df) > 0:
            print(f"   - Title: {df.iloc[0].get('title', 'N/A')}", flush=True)
            print(f"   - Published: {df.iloc[0].get('publish', 'N/A')}", flush=True)
            print(f"   - Slug: {df.iloc[0].get('slug', 'N/A')}", flush=True)
        print()
    except Exception as e:
        print(f"\n❌ ERROR: Failed to parse CSV file", flush=True)
        print(f"Error details: {e}", flush=True)
        print("\nAttempting to read first few lines of CSV for debugging:", flush=True)
        try:
            with open("temp_export.csv", "r", encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i < 10:
                        print(f"Line {i+1}: {line[:100]}...", flush=True)
        except Exception as debug_e:
            print(f"Could not read CSV for debugging: {debug_e}", flush=True)
        return

    # Load already processed articles
    processed_articles = load_processed_articles()
    print(f"📝 Already processed: {len(processed_articles)} articles\n", flush=True)

    processed_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0

    for idx, row in df.iterrows():
        try:
            # Only process published articles
            if str(row.get('publish', '')).lower() != 'true':
                skipped_count += 1
                continue

            # Extract data
            uid = str(row['uid'])
            title = str(row['title'])
            content = str(row['content'])
            pub_date_str = str(row['published date'])
            slug = str(row['slug'])

            # Calculate content hash to detect changes
            content_hash = get_content_hash(content)

            # Check if article was already processed
            if uid in processed_articles:
                if processed_articles[uid] == content_hash:
                    # Article unchanged - skip
                    skipped_count += 1
                    continue
                else:
                    # Article changed - reprocess
                    print(f"[{idx+1}/{len(df)}] 🔄 UPDATE: {slug} (content changed)", flush=True)

            # Format date for folder name (YYYY-MM-DD)
            try:
                dt = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
                date_prefix = dt.strftime("%Y-%m-%d")
            except:
                date_prefix = "0000-00-00"

            # Create folder: YYYY-MM-DD-title
            folder_name = f"{date_prefix}-{clean_filename(slug)}"
            post_dir = BASE_DIR / folder_name
            post_dir.mkdir(parents=True, exist_ok=True)

            if uid not in processed_articles:
                print(f"[{idx+1}/{len(df)}] ✨ NEW: {folder_name}", flush=True)
            else:
                print(f"[{idx+1}/{len(df)}] 🔄 UPDATE: {folder_name}", flush=True)

            # Find and download images in content
            # Searches for Markdown ![]() and HTML <img src="">
            img_urls = re.findall(r'src="([^"]+)"|!\[.*?\]\((.*?)\)', content)
            for urls in img_urls:
                url = urls[0] or urls[1]
                if url and url.startswith("http"):
                    download_file(url, post_dir)

            # Create index.md with complete frontmatter
            with open(post_dir / "index.md", "w", encoding="utf-8") as f:
                f.write("---\n")
                # Add all columns from CSV dynamically to frontmatter
                for col in df.columns:
                    if col != 'content':  # Content goes below frontmatter
                        val = str(row[col])
                        # Escape quotes and handle NaN
                        if val == 'nan':
                            val = ''
                        val = val.replace('"', '\\"')
                        f.write(f"{col.replace(' ', '_')}: \"{val}\"\n")
                f.write("---\n\n")
                f.write(content)

            # Mark article as processed
            if uid in processed_articles:
                # Update
                update_processed_article(uid, content_hash)
                updated_count += 1
            else:
                # New
                save_processed_article(uid, content_hash)
                processed_count += 1

            print(f"  ✅ Done!\n", flush=True)

        except Exception as e:
            print(f"  ❌ Error: {e}\n", flush=True)
            error_count += 1

    print("=" * 60, flush=True)
    print(f"✨ Backup Complete!", flush=True)
    print(f"  ✨ New articles: {processed_count}", flush=True)
    print(f"  🔄 Updated articles: {updated_count}", flush=True)
    print(f"  ⏭️  Skipped (unchanged/unpublished): {skipped_count}", flush=True)
    print(f"  ❌ Errors: {error_count}", flush=True)
    print("=" * 60, flush=True)

if __name__ == "__main__":
    main()
