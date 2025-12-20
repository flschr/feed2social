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

EXCLUDE = ['https://fischr.org/', 'https://fischr.org/blog/', 'https://fischr.org/fotos/', 'https://fischr.org/about/']

def get_b2_bucket():
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", B2_KEY_ID, B2_APPLICATION_KEY)
    return b2_api.get_bucket_by_name(B2_BUCKET_NAME)

def run_full_backup():
    print("🚀 Starte Full Backup (Clean Markdown & WebP Fix)...")
    bucket = get_b2_bucket()
    
    r = requests.get(SITEMAP_URL, timeout=15)
    sitemap_soup = BeautifulSoup(r.content, 'xml')
    
    entries = []
    for url_tag in sitemap_soup.find_all('url'):
        loc = url_tag.find('loc').text
        lastmod = url_tag.find('lastmod').text if url_tag.find('lastmod') else "0000-00-00"
        entries.append({'url': loc, 'date': lastmod})

    for entry in entries:
        url = entry['url']
        if url in EXCLUDE: continue
        
        try:
            raw_slug = url.strip('/').split('/')[-1]
            folder_name = f"{entry['date']}-{raw_slug}"

            res = requests.get(url, timeout=10)
            soup = BeautifulSoup(res.content, 'html.parser')
            
            content_area = soup.find('main') or soup.find('article')
            if not content_area: continue

            # --- CLEANUP ---
            # Entferne Name/Header und das ursprüngliche H1
            for unwanted in content_area.find_all(['header', 'h1']):
                unwanted.decompose()
            
            # Text für Hashtag-Extraktion vor der MD-Umwandlung sichern
            full_text = content_area.get_text()
            tags = re.findall(r'#\w+', full_text)
            tags_str = ", ".join(tags) if tags else ""

            # --- BILDER ---
            for i, img in enumerate(content_area.find_all('img')):
                img_url = img.get('src')
                if not img_url: continue
                if img_url.startswith('/'): img_url = "https://fischr.org" + img_url
                
                try:
                    img_data = requests.get(img_url, timeout=10).content
                    # Sauberer Dateiendungs-Fix
                    if 'webp' in img_url.lower():
                        ext = 'webp'
                    else:
                        ext = img_url.split('.')[-1].split('?')[0][:3].lower()
                    
                    bucket.upload_bytes(img_data, f"{folder_name}/img_{i}.{ext}")
                except: pass

            # --- MARKDOWN ---
            # ATX Style erzwingt # Headings
            markdown_main = md(str(content_area), headings_style='ATX').strip()
            
            # Entferne das Datum im Text (z.B. *19 Dec, 2025*)
            markdown_main = re.sub(r'\*\d{1,2} [A-Z][a-z]{2}, \d{4}\*', '', markdown_main).strip()

            final_md = f"""---
Title: {raw_slug.replace('-', ' ').title()}
URL: {url}
Date: {entry['date']}
Tags: {tags_str}
---

{markdown_main}
"""
            # Direkt im Artikel-Ordner speichern
            bucket.upload_bytes(final_md.encode('utf-8'), f"{folder_name}/article.md")
            print(f"   ✅ {folder_name} gesichert.")
            
        except Exception as e:
            print(f"❌ Fehler bei {url}: {e}")

if __name__ == "__main__":
    run_full_backup()