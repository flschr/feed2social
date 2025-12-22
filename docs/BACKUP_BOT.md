# Backup Bot

The Backup Bot automatically exports all your Bear Blog posts as Markdown files with images to this repository.

---

## How It Works

The Backup Bot works **independently from the Social Bot's feed configuration**. While the Social Bot uses RSS feeds with custom filters (configured in `config.json`), the Backup Bot takes a different approach:

- The Backup Bot downloads the complete blog export directly from your Bear Blog dashboard
- This CVS contains all published (and unplublished) articles. By default the bot backs up **every published** article.
- This backup is highly reliable, as we don't need to parse and convert RSS feeds or website HTML. Bear Blog already provides clean, structured CSV data.

**Detailed Steps**
1. Downloads your blog's CSV export from your Bear Blog dashboard
2. Parses each published article
3. Creates a folder per post: `YYYY-MM-DD-slug/`
4. Saves content as `index.md` with YAML frontmatter
5. Downloads all images referenced in the post (all common formats)
6. Optionally downloads linked files (PDFs, etc.) if enabled
7. Tracks processed articles to avoid duplicates

---

## Configuration

### Central Config (`config.yaml`)

```yaml
blog:
  bearblog_username: "your-username"

backup:
  folder: "blog-backup"
  save_debug_csv: false

  # Optional: Download linked files (PDFs, documents, etc.)
  linked_files:
    enabled: false
    allowed_extensions:
      - pdf
      - epub
      - zip
    allowed_domains:
      - "bear-images.sfo2.cdn.digitaloceanspaces.com"
```

| Setting | Description | Default |
|---------|-------------|---------|
| `backup.folder` | Directory for blog post backups | `blog-backup` |
| `backup.save_debug_csv` | Save the raw CSV export for debugging | `false` |
| `backup.linked_files.enabled` | Download linked files (PDFs, etc.) | `false` |
| `backup.linked_files.allowed_extensions` | File extensions to download | `[]` |
| `backup.linked_files.allowed_domains` | Domains to download from | `[]` |

### Linked Files Backup

By default, the Backup Bot downloads **images** in all common formats (jpg, png, webp, gif, etc.) automatically.

If you want to also backup **linked files** like PDFs, EPUBs, or ZIPs, you can enable the `linked_files` feature:

1. Set `enabled: true`
2. Add allowed file extensions to `allowed_extensions`
3. Add trusted domains to `allowed_domains` (for security)

> [!NOTE]
> When you enable this feature, the bot will also check **existing articles** for linked files on the next run. Files that already exist won't be downloaded again.

> [!CAUTION]
> **About `save_debug_csv`**: The CSV export from Bear Blog contains **all articles, including unpublished drafts**. If you enable this option, draft content will be saved to `bots/backup_bot/last_export.csv` and committed to your repository. Only enable this for debugging purposes, and be aware that in a public repository, your unpublished drafts would be visible to anyone (including in git history).

### GitHub Secret

| Secret | Description |
|--------|-------------|
| `BEAR_COOKIE` | Your Bear Blog session cookie |

---

## Getting the Bear Blog Cookie

1. Log in to `https://bearblog.dev/dashboard/`
2. Open Developer Tools (F12)
3. Go to **Application** (Chrome) or **Storage** (Firefox)
4. Click **Cookies** → `bearblog.dev`
5. Copy the `sessionid` value
6. Add to GitHub Secrets as `BEAR_COOKIE`

You can use either format:
- `sessionid=YOUR_VALUE`
- `YOUR_VALUE` (the prefix is added automatically)

> [!IMPORTANT]  
> The cookie has a fixed expiration date. Once it invalidates, you must replace the session ID with the current one issued by Bear Blog. With a 3-month lifespan, this update is required roughly four times per year.
---

## Backup Folder Structure

```
blog-backup/
├── 2025-01-15-my-first-post/
│   ├── index.md
│   └── image.webp
├── 2025-01-20-another-post/
│   ├── index.md
│   ├── photo1.webp
│   └── photo2.webp
└── ...
```

Each `index.md` contains:
- YAML frontmatter with all metadata (title, date, tags, etc.)
- Full post content in Markdown

---

## Scheduling

The backup runs:
- **Weekly**: Every Monday at midnight UTC (default, feel free to adopt)
- **After new posts**: When the Social Bot detects new articles in any RSS feed, it triggers the Backup Bot to run afterwards - ensuring your backup stays current
- **Manually**: Via GitHub Actions → Run workflow

---

## Related Documentation

- [Social Bot](SOCIAL_BOT.md) - Automatic social media posting & feed configuration
- [Cloudflare Worker](CLOUDFLARE_WORKER.md) - Instant trigger setup
