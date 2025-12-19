import os
import requests
import re
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from b2sdk.v2 import InMemoryAccountInfo, B2Api

# --- KONFIGURATION ---
B2_KEY_ID = os.getenv('B2_KEY_ID')
B2_APPLICATION_KEY = os.getenv('B2_APPLICATION_KEY')
B2_BUCKET_NAME = os.getenv('B2_BUCKET_NAME')
SITEMAP_URL = "https://fischr.org/sitemap.xml"

# Ausschlüsse (Seiten, keine Artikel)
EXCLUDE = ['https://fischr.org/', 'https://fischr.org/blog/', 'https://fischr.org/fotos/', 'https://fischr.org/about/']

def get_b2_bucket():
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", B2_KEY_ID, B2_APPLICATION_KEY)
    return b2_api.get_bucket_by_name(B2_BUCKET_NAME)

def slugify(text):
    return re.sub(r'[\W_]+', '-', text.lower()).strip('-')

def run_full_backup():
    print("🚀 Starte MANUELLES FULL BACKUP (ignoriert posted.txt)...")
    bucket = get_b2_bucket()
    
    # Sitemap laden
    try:
        r = requests.get(SITEMAP_URL, timeout=15)
        r.raise_for_status()
        sitemap_soup = BeautifulSoup(r.content, 'xml')
        urls = [loc.text for loc in sitemap_soup.find_all('loc')]
    except Exception as e:
        print(f"❌ Fehler beim Laden der Sitemap: {e}")
        return

    count = 0
    for url in urls:
        if url in EXCLUDE:
            continue
        
        try:
            print(f"📥 Verarbeite: {url}")
            res = requests.get(url, timeout=10)
            soup = BeautifulSoup(res.content, 'html.parser')
            
            title = soup.find('h1').text if soup.find('h1') else url.split('/')[-2]
            title_slug = slugify(title)
            
            # Bearblog spezifischer Content-Bereich
            content_area = soup.find('main') or soup.find('article')
            if not content_area: 
                print(f"   ⚠️ Kein Content-Bereich gefunden für {url}")
                continue

            # 1. Bilder sichern
            for i, img in enumerate(content_area.find_all('img')):
                img_url = img.get('src')
                if not img_url: continue
                if img_url.startswith('/'): img_url = "https://fischr.org" + img_url
                
                try:
                    img_data = requests.get(img_url, timeout=10).content
                    ext = img_url.split('.')[-1].split('?')[0][:3]
                    # Pfad: backups/titel/images/img_0.jpg
                    bucket.upload_bytes(img_data, f"backups/{title_slug}/images/img_{i}.{ext}")
                except: 
                    print(f"   ⚠️ Bild-Download fehlgeschlagen: {img_url}")

            # 2. Markdown sichern
            markdown_text = f"# {title}\n\nURL: {url}\n\n" + md(str(content_area))
            bucket.upload_bytes(markdown_text.encode('utf-8'), f"backups/{title_slug}/article.md")
            
            count += 1
            print(f"   ✅ {title_slug} gesichert.")
            
        except Exception as e:
            print(f"❌ Fehler bei {url}: {e}")

    print(f"\n✨ FULL BACKUP abgeschlossen. {count} Artikel verarbeitet.")

if __name__ == "__main__":
    run_full_backup()