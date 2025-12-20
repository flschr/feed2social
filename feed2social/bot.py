import feedparser, json, os, re, requests
from bs4 import BeautifulSoup
from atproto import Client, client_utils, models
from mastodon import Mastodon
import logging
from contextlib import contextmanager
from time import sleep

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

session = requests.Session()
session.headers.update({'User-Agent': 'feed2social/1.0'})

# --- CONSTANTS ---
MAX_IMAGE_SIZE = 5_000_000 
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3

# Define the path for the posted.txt in the parent directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTED_FILE = os.path.join(BASE_DIR, 'posted.txt')
LOCK_FILE = os.path.join(BASE_DIR, 'posted.txt.lock')
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')

@contextmanager
def posted_file_lock():
    """Simple file lock to prevent concurrent write access."""
    retry = 0
    while os.path.exists(LOCK_FILE) and retry < 10:
        sleep(0.5)
        retry += 1
    try:
        open(LOCK_FILE, 'w').close()
        yield
    finally:
        if os.path.exists(LOCK_FILE): os.remove(LOCK_FILE)

def is_posted(link):
    """Checks if a URL is already listed in posted.txt."""
    if not os.path.exists(POSTED_FILE): return False
    with posted_file_lock():
        with open(POSTED_FILE, 'r') as f:
            return link in f.read()

def mark_as_posted(link):
    """Adds a URL to the posted.txt file in the main directory."""
    with posted_file_lock():
        with open(POSTED_FILE, 'a') as f:
            f.write(link + '\n')
    logger.info(f"Marked as posted: {link}")

def get_html_content(entry):
    """Extracts text content from RSS entry and removes images."""
    try:
        html = entry.content[0].value if hasattr(entry, 'content') else entry.get('summary', '')
        soup = BeautifulSoup(html, "html.parser")
        for img in soup.find_all('img'): img.decompose()
        return soup.get_text(separator=' ')
    except: return ""

def get_first_image(entry):
    """Extracts the first image URL from the entry content."""
    try:
        html = entry.content[0].value if hasattr(entry, 'content') else entry.get('summary', '')
        match = re.search(r'<img [^>]*src="([^"]+)"', html)
        return match.group(1) if match else None
    except: return None

def download_image(img_url, save_path="temp.jpg"):
    """Downloads an image for posting, observing size limits."""
    try:
        r = session.get(img_url, timeout=REQUEST_TIMEOUT, stream=True)
        r.raise_for_status()
        if int(r.headers.get('content-length', 0)) > MAX_IMAGE_SIZE: return None
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
        return save_path
    except: return None

def get_og_metadata(url):
    """Retrieves Open Graph metadata for link previews."""
    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(r.text, 'html.parser')
        t = soup.find("meta", property="og:title")
        d = soup.find("meta", property="og:description")
        i = soup.find("meta", property="og:image")
        return {
            "title": t["content"] if t else "Blog post",
            "description": d["content"] if d else "",
            "image_url": i["content"] if i else None
        }
    except: return None

def submit_to_indexnow(url):
    """Submits the URL to IndexNow for search engine indexing."""
    key = os.getenv('INDEXNOW_KEY')
    if not key:
        logger.warning("INDEXNOW_KEY secret missing!")
        return
    payload = {"host": "fischr.org", "key": key, "urlList": [url]}
    try:
        r = session.post("https://www.bing.com/indexnow", json=payload, timeout=REQUEST_TIMEOUT)
        logger.info(f"IndexNow Status: {r.status_code} for {url}")
    except Exception as e:
        logger.error(f"IndexNow Error: {e}")

def post_to_bluesky(text, link, img_path):
    """Authenticates and posts text/media to BlueSky."""
    client = Client()
    client.login(os.getenv('BSKY_HANDLE'), os.getenv('BSKY_PW'))
    tb = client_utils.TextBuilder()
    if link and link in text:
        parts = text.split(link)
        tb.text(parts[0][:150]).link(link, link)
        if len(parts) > 1: tb.text(parts[1])
    else: tb.text(text[:290])
    embed = None
    if img_path and os.path.exists(img_path):
        with open(img_path, 'rb') as f:
            upload = client.upload_blob(f.read())
            embed = models.AppBskyEmbedImages.Main(images=[models.AppBskyEmbedImages.Image(alt="", image=upload.blob)])
    elif link:
        meta = get_og_metadata(link)
        if meta:
            thumb = None
            if meta["image_url"]:
                try: thumb = client.upload_blob(session.get(meta["image_url"]).content).blob
                except: pass
            embed = models.AppBskyEmbedExternal.Main(external=models.AppBskyEmbedExternal.External(
                title=meta["title"], description=meta["description"], uri=link, thumb=thumb
            ))
    client.send_post(text=tb, embed=embed)
    logger.info("BlueSky Success")

def post_to_mastodon(text, img_path):
    """Authenticates and posts text/media to Mastodon."""
    m = Mastodon(access_token=os.getenv('MASTO_TOKEN'), api_base_url='https://mastodon.social')
    ids = [m.media_post(img_path)['id']] if img_path else []
    m.status_post(status=text[:500], media_ids=ids)
    logger.info("Mastodon Success")

def run():
    """Main execution loop for all configured feeds."""
    logger.info("=== Bot Start ===")
    if not os.path.exists(CONFIG_FILE):
        logger.error(f"Config file not found at {CONFIG_FILE}")
        return
        
    with open(CONFIG_FILE) as f: config = json.load(f)
    for cfg in config:
        feed = feedparser.parse(session.get(cfg['url']).content)
        for entry in feed.entries:
            if is_posted(entry.link): continue
            
            # Filter Check (Title + Content)
            text_to_check = (entry.title + " " + entry.get('summary', '')).lower()
            if any(w.lower() in text_to_check for w in cfg.get('exclude', [])): continue
            if cfg.get('include') and not any(w.lower() in text_to_check for w in cfg['include']): continue

            logger.info(f"Processing: {entry.title}")
            img_path = download_image(get_first_image(entry)) if cfg.get('include_images') else None
            msg = cfg['template'].format(title=entry.title, link=entry.link, content=get_html_content(entry))
            
            try:
                # Dispatch Social Media Posts
                if "bluesky" in cfg.get('targets', []): post_to_bluesky(msg, entry.link, img_path)
                if "mastodon" in cfg.get('targets', []): post_to_mastodon(msg, img_path)
                
                # IndexNow (Always executed even if targets are empty)
                submit_to_indexnow(entry.link)
                mark_as_posted(entry.link)
                
            except Exception as e: logger.error(f"Error: {e}")
            finally: 
                if img_path and os.path.exists(img_path): os.remove(img_path)
    logger.info("=== Bot End ===")

if __name__ == "__main__": run()