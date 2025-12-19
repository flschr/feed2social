import feedparser, json, os, re, requests
from bs4 import BeautifulSoup
from atproto import Client, models, client_utils
from mastodon import Mastodon

def get_html_content(entry):
    html = entry.content[0].value if hasattr(entry, 'content') else entry.get('summary', '')
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all('img'): img.decompose() # Bilder entfernen (da nativer Upload)
    return str(soup)

def get_first_image(entry):
    html = entry.content[0].value if hasattr(entry, 'content') else entry.get('summary', '')
    match = re.search(r'<img [^>]*src="([^"]+)"', html)
    return match.group(1) if match else None

def post_to_bluesky(text, img_path):
    client = Client()
    client.login(os.getenv('BSKY_HANDLE'), os.getenv('BSKY_PW'))
    # TextBuilder erkennt Links automatisch und macht sie zu klickbaren Facets
    tb = client_utils.TextBuilder().text(text[:300]) 
    embed = None
    if img_path:
        with open(img_path, 'rb') as f:
            upload = client.upload_blob(f.read())
            embed = models.AppBskyEmbedImages.Main(images=[models.AppBskyEmbedImages.Image(alt="", image=upload.blob)])
    client.send_post(text=tb, embed=embed)

def post_to_mastodon(html_text, img_path):
    m = Mastodon(access_token=os.getenv('MASTO_TOKEN'), api_base_url='https://mastodon.social')
    media_ids = [m.media_post(img_path)] if img_path else []
    # Der Trick für klickbare HTML-Links
    m.status_post(status=html_text, media_ids=media_ids, content_type='text/html')

def check_filter(entry, include, exclude):
    text = (entry.title + " " + entry.get('summary', '')).lower()
    tags = [t.term.lower() for t in entry.tags] if hasattr(entry, 'tags') else []
    if any(w.lower() in text or w.lower() in tags for w in exclude): return False
    if not include: return True
    return any(w.lower() in text or w.lower() in tags for w in include)

def run():
    with open('config.json') as f: config = json.load(f)
    if not os.path.exists('posted.txt'): open('posted.txt', 'w').close()
    with open('posted.txt', 'r') as f: posted = f.read().splitlines()

    for cfg in config:
        feed = feedparser.parse(cfg['url'])
        for entry in feed.entries:
            if entry.link in posted: continue
            if check_filter(entry, cfg.get('include', []), cfg.get('exclude', [])):
                img_path = None
                if cfg.get('include_images'):
                    img_url = get_first_image(entry)
                    if img_url:
                        r = requests.get(img_url); img_path = "temp.jpg"
                        with open(img_path, 'wb') as f: f.write(r.content)

                html_content = get_html_content(entry)
                
                if "bluesky" in cfg['targets']: post_to_bluesky(entry.title + "\n\n" + entry.link, img_path)
                if "mastodon" in cfg['targets']: post_to_mastodon(html_content, img_path)
                
                with open('posted.txt', 'a') as f: f.write(entry.link + "\n")
                if img_path and os.path.exists(img_path): os.remove(img_path)
                break # Nur ein Post pro Durchlauf/Feed, um Spam zu vermeiden

if __name__ == "__main__": run()