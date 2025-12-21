# Backup Bot

The Backup Bot automatically exports all your Bear Blog posts as Markdown files with images to this repository.

---

## How It Works

1. Downloads your blog's CSV export from your Bear Blog dashboard
2. Parses each published article
3. Creates a folder per post: `YYYY-MM-DD-slug/`
4. Saves content as `index.md` with YAML frontmatter
5. Downloads all images referenced in the post
6. Tracks processed articles to avoid duplicates

---

## Data Source

The Backup Bot works **independently from the Social Bot's feed configuration**. While the Social Bot uses RSS feeds with custom filters (configured in `config.json`), the Backup Bot takes a different approach:

- **Direct CSV export**: Downloads the complete blog export directly from Bear Blog's dashboard
- **All published posts**: Backs up every published article, regardless of tags or categories
- **Highly reliable**: No RSS parsing needed - Bear Blog provides clean, structured CSV data

This means your `config.json` feed settings only affect which posts get shared to social media. The backup always captures your entire blog.

---

## Configuration

### Central Config (`config.yaml`)

```yaml
blog:
  bearblog_username: "your-username"

backup:
  folder: "blog-backup"
```

The `backup.folder` setting lets you choose where your blog posts are stored. Default is `blog-backup`.

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

- [Social Bot](SOCIAL_BOT.md) - Automatic social media posting
- [Feed Configuration](CONFIGURATION.md) - Configure RSS feeds
- [Cloudflare Worker](CLOUDFLARE_WORKER.md) - Instant trigger setup
