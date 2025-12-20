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
BLOG_INDEX_URL = "https://fischr.org/blog/"

def get_b2_bucket():
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", B2_KEY_ID, B2_APPLICATION_KEY)
    return b2_api.get_bucket_by_name(B2_BUCKET_NAME)

def parse_blog_index():
    print(f"🔍 Scanne Blog-Index: {BLOG_INDEX_URL}")
    r = requests.get(BLOG_INDEX_URL, timeout=15)
    soup = BeautifulSoup(r.content, 'html.parser')
    
    articles = []
    # Bearblog listet Artikel meist in <li> oder direkt als <a> mit Datum daneben
    # Wir suchen nach Links innerhalb des main/article Bereichs
    content = soup.find('main') or soup.find('body')
    
    for link in content.find_all('a', href=True):
        url = link['href']
        if not url.startswith('http'):
            url = "https://fischr.org" + url
        
        # Wir ignorieren die Standard-Navigation
        if any(x in url for x in ['/blog/', '/about/', '/fotos/', 'tags']):
            continue

        # Datum finden: Bearblog schreibt das Datum oft direkt vor/nach den Link
        # Wir suchen im Elternelement nach dem Format "YYYY-MM-DD" oder "DD Mon, YYYY"
        parent_text = link.parent.get_text()
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', parent_text) # YYYY-MM-DD
        
        if date_match:
            publish_date = date_match.group(1)
            articles.append({'url': url, 'date': publish_date})
            
    return articles

def run_full_backup():
    print("🚀 Starte Full Backup via /blog Index...")
    bucket = get_b2_bucket()
    articles = parse_blog_index()
    
    if not articles:
        print("⚠️ Keine Artikel auf /blog gefunden. Prüfe die HTML-Struktur.")
        return

    print(f"✅ {len(articles)} Artikel gefunden.")

    for entry in articles:
        url = entry['url']
        date = entry['date']
        raw_slug = url.strip('/').split('/')[-1]
        folder_name = f"{date}-{raw_slug}"

        try:
            print(f"📥 Sichere: {folder_name}")
            res = requests.get(url, timeout=10)
            soup = BeautifulSoup(res.content, 'html.parser')
            content_area = soup.find('main') or soup.find('article')
            
            if not content_area: continue

            # Tags finden & Cleanup
            tags = re.findall(r'#\w+', content_area.get_text())
            tags_str = ", ".join(tags) if tags else ""
            for unwanted in content_area.find_all(['header', 'h1']):
                unwanted.decompose()

            # Bilder (Flat & WebP Fix)
            for i, img in enumerate(content_area.find_all('img')):
                img_url = img.get('src')
                if not img_url: continue
                if img_url.startswith('/'): img_url = "https://fischr.org" + img_url
                try:
                    img_data = requests.get(img_url, timeout=10).content
                    ext = 'webp' if 'webp' in img_url.lower() else img_url.split('.')[-1].split('?')[0][:3].lower()
                    bucket.upload_bytes(img_data, f"{folder_name}/img_{i}.{ext}")
                except: pass

            # Markdown (Strict ATX)
            markdown_main = md(str(content_area), headings_style='ATX').strip()
            # Datum im Text entfernen
            markdown_main = re.sub(r'\*\d{1,2} [A-Z][a-z]{2}, \d{4}\*', '', markdown_main).strip()

            final_md = f"""---
Title: {raw_slug.replace('-', ' ').title()}
URL: {url}
Date: {date}
Tags: {tags_str}
---

{markdown_main}
"""
            bucket.upload_bytes(final_md.encode('utf-8'), f"{folder_name}/article.md")
            
        except Exception as e:
            print(f"❌ Fehler bei {url}: {e}")

    print("\n✨ FULL BACKUP abgeschlossen.")

if __name__ == "__main__":
    run_full_backup()