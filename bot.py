import feedparser, json, os, re, requests
from bs4 import BeautifulSoup
from atproto import Client, client_utils, models
from mastodon import Mastodon

def get_html_content(entry):
    """Wandelt HTML in sauberen Text um."""
    html = entry.content[0].value if hasattr(entry, 'content') else entry.get('summary', '')
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all('img'): img.decompose()
    return soup.get_text(separator=' ')

def get_first_image(entry):
    """Sucht das erste Beitragsbild im Feed."""
    html = entry.content[0].value if hasattr(entry, 'content') else entry.get('summary', '')
    match = re.search(r'<img [^>]*src="([^"]+)"', html)
    return match.group(1) if match else None

def get_og_metadata(url):
    """Extrahiert OG-Daten für die BlueSky Vorschau-Karte."""
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.find("meta", property="og:title")
        desc = soup.find("meta", property="og:description")
        img = soup.find("meta", property="og:image")
        return {
            "title": title["content"] if title else "Blogartikel",
            "description": desc["content"] if desc else "",
            "image_url": img["content"] if img else None
        }
    except: return None

def submit_to_indexnow(url):
    """Übermittelt die URL via IndexNow (Bing/Yandex)."""
    key = os.getenv('INDEXNOW_KEY')
    if not key: return
    
    payload = {
        "host": "fischr.org",
        "key": key,
        "keyLocation": f"https://fischr.org/{key}.txt", # Falls DNS genutzt wird, ist dies optional, schadet aber nicht
        "urlList": [url]
    }
    try:
        r = requests.post("https://www.bing.com/indexnow", json=payload, timeout=10)
        print(f"IndexNow Submission: {url} (Status: {r.status_code})")
    except Exception as e:
        print(f"IndexNow Fehler: {e}")

def post_to_bluesky(text, link, img_path):
    """Postet auf BlueSky mit klickbarem Link und Vorschau-Karte."""
    client = Client()
    client.login(os.getenv('BSKY_HANDLE'), os.getenv('BSKY_PW'))
    tb = client_utils.TextBuilder()
    
    # Klickbaren Link im Text erzeugen
    if link and link in text:
        parts = text.split(link)
        tb.text(parts[0][:150]) # Vorsorgliches Kürzen
        tb.link(link, link)
        if len(parts) > 1: tb.text(parts[1])
    else:
        tb.text(text[:290])

    embed = None
    if img_path:
        # Priorität A: Bild-Post (keine Karte möglich)
        with open(img_path, 'rb') as f:
            upload = client.upload_blob(f.read())
            embed = models.AppBskyEmbedImages.Main(images=[
                models.AppBskyEmbedImages.Image(alt="", image=upload.blob)
            ])
    elif link:
        # Priorität B: Link-Post mit Vorschau-Karte
        meta = get_og_metadata(link)
        if meta:
            thumb_blob = None
            if meta["image_url"]:
                try:
                    img_r = requests.get(meta["image_url"], timeout=5)
                    thumb_blob = client.upload_blob(img_r.content).blob
                except: pass
            embed = models.AppBskyEmbedExternal.Main(external=models.AppBskyEmbedExternal.External(
                title=meta["title"], description=meta["description"], uri=link, thumb=thumb_blob
            ))

    client.send_post(text=tb, embed=embed)

def post_to_mastodon(text, img_path):
    """Postet auf Mastodon (Plain Text für native Vorschau)."""
    m = Mastodon(access_token=os.getenv('MASTO_TOKEN'), api_base_url='https://mastodon.social')
    media_ids = [m.media_post(img_path)['id']] if img_path else []
    m.status_post(status=text[:500], media_ids=media_ids)

def check_filter(entry, include, exclude):
    """Filtert Artikel nach Keywords/Tags."""
    text = (entry.title + " " + entry.get('summary', '')).lower()
    tags = [t.term.lower() for t in entry.tags] if hasattr(entry, 'tags') else []
    if any(w.lower() in text or w.lower() in tags for w in exclude): return False
    return not include or any(w.lower() in text or w.lower() in tags for w in include)

def run():
    """Hauptprozess des Bots."""
    with open('config.json') as f: config = json.load(f)
    if not os.path.exists('posted.txt'): open('posted.txt', 'w').close()
    with open('posted.txt', 'r') as f: posted = f.read().splitlines()
    
    processed_in_run = set()
    for cfg in config:
        print(f"Prüfe Feed: {cfg['name']}")
        feed = feedparser.parse(cfg['url'])
        
        for entry in feed.entries:
            if entry.link in posted or entry.link in processed_in_run: continue
            
            if check_filter(entry, cfg.get('include', []), cfg.get('exclude', [])):
                print(f"Poste: {entry.title}")
                img_path = None
                if cfg.get('include_images'):
                    img_url = get_first_image(entry)
                    if img_url:
                        try:
                            r = requests.get(img_url, timeout=10)
                            img_path = "temp.jpg"
                            with open(img_path, "wb") as f: f.write(r.content)
                        except: img_path = None

                clean_body = get_html_content(entry)
                msg = cfg['template'].format(title=entry.title, link=entry.link, content=clean_body)
                
                try:
                    if "bluesky" in cfg['targets']: post_to_bluesky(msg, entry.link, img_path)
                    if "mastodon" in cfg['targets']: post_to_mastodon(msg, img_path)
                    
                    submit_to_indexnow(entry.link)
                    
                    # SICHERES SCHREIBEN: Zeilenumbruch prüfen
                    with open('posted.txt', 'r+') as f:
                        content = f.read()
                        if content and not content.endswith('\n'):
                            f.write('\n')
                        f.write(entry.link + '\n')
                    
                    processed_in_run.add(entry.link)
                except Exception as e:
                    print(f"Fehler: {e}")
                
                if img_path and os.path.exists(img_path): os.remove(img_path)

if __name__ == "__main__": run()