import os
import requests
import re
import feedparser
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from b2sdk.v2 import InMemoryAccountInfo, B2Api
from datetime import datetime

# --- PFAD-LOGIK ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTED_FILE_PATH = os.path.join(BASE_DIR, 'posted.txt')

# --- KONFIGURATION ---
B2_KEY_ID = os.getenv('B2_KEY_ID')
B2_APPLICATION_KEY = os.getenv('B2_APPLICATION_KEY')
B2_BUCKET_NAME = os.getenv('B2_BUCKET_NAME')
RSS_FEED_URL = "https://fischr.org/feed/"

def get_b2_bucket():
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", B2_KEY_ID, B2_APPLICATION_KEY)
    return b2_api.get_bucket_by_name(B2_BUCKET_NAME)

def run_regular_backup():
    print("🚀 Prüfe RSS-Feed auf neue Artikel...")
    bucket = get_b2_bucket()
    feed = feedparser.parse(RSS_FEED_URL)
    
    if not os.path.exists(POSTED_FILE_PATH):
        open(POSTED_FILE_PATH, 'w').close()

    with open(POSTED_FILE_PATH, 'r') as f:
        already_done = f.read().splitlines()

    new_posts = 0

    for entry in feed.entries:
        if entry.link in already_done:
            continue
        
        # Datum aus RSS extrahieren (YYYY-MM-DD)
        dt = entry.published_parsed
        date_str = f"{dt.tm_year}-{dt.tm_mon:02d}-{dt.tm_mday:02d}"
        
        # Slug aus URL generieren
        raw_slug = entry.link.strip('/').split('/')[-1]
        folder_name = f"{date_str}-{raw_slug}"

        print(f"📥 Neuer Post gefunden: {entry.title} -> {folder_name}")
        
        html_content = entry.content[0].value if hasattr(entry, 'content') else entry.summary
        soup = BeautifulSoup(html_content, "html.parser")

        # --- BILDER (Flat in Root) ---
        img_tags = soup.find_all('img')
        for i, img in enumerate(img_tags):
            img_url = img.get('src')
            if not img_url: continue
            if img_url.startswith('/'): img_url = "https://fischr.org" + img_url
            
            try:
                img_data = requests.get(img_url, timeout=10).content
                if 'webp' in img_url.lower():
                    ext = 'webp'
                else:
                    ext = img_url.split('.')[-1].split('?')[0][:3].lower()
                
                bucket.upload_bytes(img_data, f"{folder_name}/img_{i}.{ext}")
            except: pass

        # --- MARKDOWN (Clean & Strict ATX) ---
        tags = re.findall(r'#\w+', html_content)
        tags_str = ", ".join(tags) if tags else ""

        markdown_main = md(
            html_content, 
            headings_style='ATX'
        ).strip()
        
        # Datum im Text entfernen (*19 Dec, 2025*)
        markdown_main = re.sub(r'\*\d{1,2} [A-Z][a-z]{2}, \d{4}\*', '', markdown_main).strip()

        final_md = f"""---
Title: {entry.title}
URL: {entry.link}
Date: {date_str}
Tags: {tags_str}
---

{markdown_main}
"""
        # Speichern im Bucket
        bucket.upload_bytes(final_md.encode('utf-8'), f"{folder_name}/article.md")
        
        # In posted.txt loggen
        with open(POSTED_FILE_PATH, 'a') as f:
            f.write(entry.link + '\n')
        
        new_posts += 1
        print(f"   ✅ {folder_name} erfolgreich gesichert.")

    if new_posts == 0:
        print("☕ Keine neuen Artikel im Feed.")

if __name__ == "__main__":
    run_regular_backup()