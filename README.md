# 🐻 Bear Blog Automation Suite

A complete automation system for Bear Blog for my blog (fischr.org) that handles **Social media distribution**, **SEO indexing**, and **automated backups** to GitHub.

---

## 🌟 Features

### 📱 Social Bot (`social_bot/`)
- **Multi-Feed RSS Monitoring**: Monitor multiple RSS feeds with individual configurations
- **Smart Social Distribution**: Automatic posting to BlueSky and Mastodon
- **Flexible Filtering**: Include/exclude rules based on titles, hashtags, and RSS categories
- **Media Support**: Automatically downloads and uploads the first image with ALT-text
- **Rich Text**: Hashtags and links are converted to native rich text on supported platforms
- **Photo Posts**: Automatically adds post content for photo posts (respecting character limits)
- **SEO Integration**: Automatic IndexNow submission for faster search engine indexing
- **Runs every 5 minutes** via GitHub Actions

### 💾 Backup Bot (`backup_bot/`)
- **Full Blog Backup**: Downloads complete blog from Bear Blog CSV export
- **Markdown Conversion**: Converts posts to clean Markdown with YAML frontmatter
- **Image Archival**: Concurrent download of all images from posts
- **Incremental Backups**: Hash-based change detection (only updates when content changes)
- **Organized Structure**: Posts stored as `YYYY-MM-DD-slug/index.md` with images
- **Smart Triggering**: Runs weekly OR when new posts are detected by Social Bot

---

## 📂 Project Structure

```
bearblog-automation/
├── social_bot/
│   ├── social_bot.py         # Main social automation script
│   ├── config.json            # Feed configurations
│   ├── posted_articles.txt    # Tracking file (auto-generated)
│   └── requirements.txt
│
├── backup_bot/
│   ├── backup_bot.py          # Main backup script
│   ├── processed_articles.txt # Tracking file (auto-generated)
│   └── requirements.txt
│
├── blog_posts/                # Backup destination
│   └── YYYY-MM-DD-slug/
│       ├── index.md           # Post content with frontmatter
│       └── *.webp             # Images
│
└── .github/workflows/
    ├── social_bot.yml         # Runs every 5 minutes
    └── backup_bot.yml         # Runs weekly + on-trigger
```

---

## You want to use this setup for your (Bear) Blog?

### 1. Fork this Repository
Click **Fork** at the top right to create your own copy.

### 2. Configure Social Bot

Edit `social_bot/config.json` to match your feeds. You can configure multiple feeds with different rules:

```json
[
  {
    "name": "Photo Suggestions",
    "url": "https://yourblog.com/feed?q=photos",
    "include": ["photo"],
    "include_images": true,
    "template": "{content} #photography",
    "targets": ["bluesky", "mastodon"]
  },
  {
    "name": "Blog Articles",
    "url": "https://yourblog.com/feed/",
    "include": ["blog"],
    "exclude": ["draft", "private"],
    "template": "New post: {title}\n\n{link}",
    "targets": ["bluesky", "mastodon"]
  }
]
```

#### Configuration Options

| Option | Required | Description |
|--------|----------|-------------|
| `name` | Yes | Descriptive name for this feed (used in logs) |
| `url` | Yes | RSS feed URL |
| `include` | No | Only posts with these keywords in title/hashtags/categories |
| `exclude` | No | Skip posts with these keywords in title/hashtags/categories |
| `include_images` | No | `true` to attach first image with ALT-text |
| `targets` | Yes | Array: `["bluesky"]`, `["mastodon"]`, or both |
| `template` | Yes | Post format. Placeholders: `{title}`, `{link}`, `{content}` |

**Note**:
- For photo posts, `{content}` includes the full post text
- Content is automatically truncated (300 chars for BlueSky, 500 for Mastodon)
- Hashtags in templates are converted to native tags on BlueSky

### 3. Configure GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

#### Required for Social Bot
| Secret | Description |
|--------|-------------|
| `BSKY_HANDLE` | Your BlueSky handle (e.g., `user.bsky.social`) |
| `BSKY_PW` | BlueSky **App Password** (not your main password!) |
| `MASTO_TOKEN` | Mastodon Access Token |

#### Optional
| Secret | Description |
|--------|-------------|
| `INDEXNOW_KEY` | IndexNow API key for SEO (from [indexnow.org](https://www.indexnow.org)) |
| `BEAR_COOKIE` | Bear Blog session cookie (format: `sessionid=YOUR_VALUE`) |

**Getting the Bear Blog Cookie:**
1. Log in to `https://bearblog.dev/yourblog/dashboard/`
2. Open Developer Tools (F12) → Application/Storage → Cookies
3. Copy the `sessionid` value
4. Add to GitHub Secrets as: `sessionid=YOUR_VALUE`

### 4. Update Backup Bot Configuration

Edit `backup_bot/backup_bot.py` and update:

```python
CSV_URL = "https://bearblog.dev/YOUR_BLOG/dashboard/settings/?export=true"
```

If you want to customize allowed image domains, edit the `ALLOWED_IMAGE_DOMAINS` set in both scripts.

### 5. Enable GitHub Actions

1. Go to **Actions** tab
2. Click **"I understand my workflows, go ahead and enable them"**
3. The bots will now run automatically

---

## 🔧 How It Works

### Social Bot Workflow

1. **Every 5 minutes**, GitHub Actions triggers the Social Bot
2. **Fetches** all configured RSS feeds
3. **Filters** entries based on `include`/`exclude` rules
4. **Checks** `posted_articles.txt` to avoid duplicates
5. **Downloads** images (if enabled) with security checks
6. **Posts** to configured platforms with rich text formatting
7. **Submits** to IndexNow for SEO
8. **Updates** `posted_articles.txt` and commits to repository
9. **Triggers** Backup Bot if new posts were detected

### Backup Bot Workflow

Runs when:
- **Triggered** by Social Bot (new post detected)
- **Weekly** every Monday at midnight UTC
- **Manual** workflow dispatch

Process:
1. **Downloads** CSV export from Bear Blog
2. **Parses** all published articles
3. **Checks** `processed_articles.txt` for changes (SHA-256 hash)
4. **Creates** folder structure: `YYYY-MM-DD-slug/`
5. **Downloads** all images concurrently (max 5 at a time)
6. **Converts** HTML content to Markdown
7. **Adds** YAML frontmatter with all metadata
8. **Updates** tracking file and commits to repository

---

## 📜 License

MIT License - Feel free to fork and customize for your own blog!

---

## 👤 Author

Created by **[René Fischer](https://fischr.org)** for automating fischr.org.

## 🙏 Contributing

Found a bug? Have a feature request? Open an issue or submit a pull request!

---

## 📚 Learn More

- [Bear Blog](https://bearblog.dev) - Free, privacy-focused blogging
- [BlueSky API](https://docs.bsky.app) - AT Protocol documentation
- [Mastodon API](https://docs.joinmastodon.org/api/) - Mastodon documentation
- [IndexNow](https://www.indexnow.org) - Instant indexing protocol
