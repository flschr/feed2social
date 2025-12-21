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
- **Efficient Feed Checking**: ETag/Last-Modified caching to minimize unnecessary feed downloads
- **Flexible Triggering**: Runs via GitHub Actions schedule OR external triggers (Cloudflare Worker)

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
├── config.yaml                # Central configuration (edit this when forking!)
│
├── social_bot/
│   ├── social_bot.py          # Main social automation script
│   ├── config.json            # Feed configurations
│   ├── posted_articles.txt    # Tracking file (auto-generated)
│   ├── feed_cache.json        # ETag/Last-Modified cache (auto-generated)
│   └── requirements.txt
│
├── backup_bot/
│   ├── backup_bot.py          # Main backup script
│   ├── processed_articles.txt # Tracking file (auto-generated)
│   └── requirements.txt
│
├── cloudflare-worker/         # Optional: External RSS monitor
│   ├── rss-monitor.js         # Cloudflare Worker code
│   └── SETUP.md               # Detailed setup instructions
│
├── blog_posts/                # Backup destination
│   └── YYYY-MM-DD-slug/
│       ├── index.md           # Post content with frontmatter
│       └── *.webp             # Images
│
└── .github/workflows/
    ├── social_bot.yml         # Scheduled + external triggers
    └── backup_bot.yml         # Runs weekly + on-trigger
```

---

## You want to use this setup for your (Bear) Blog?

### 1. Fork this Repository
Click **Fork** at the top right to create your own copy.

### 2. Edit Central Configuration

Edit `config.yaml` in the repository root:

```yaml
blog:
  bearblog_username: "your-username"  # Your Bear Blog username

social:
  mastodon_instance: "https://mastodon.social"  # Your Mastodon instance
```

### 3. Configure Social Bot Feeds

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
- Content is automatically truncated (300 chars for BlueSky, 500 for Mastodon)
- Hashtags in templates are converted to native tags on BlueSky

### 4. Configure GitHub Secrets

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

### 5. Enable GitHub Actions

1. Go to **Actions** tab
2. Click **"I understand my workflows, go ahead and enable them"**
3. The bots will now run automatically

---

## ⚡ Optional: Cloudflare Worker for Efficient Triggering

Want even better efficiency? Use a Cloudflare Worker to trigger the bot **only when RSS feeds actually change**!

**Benefits:**
- ✅ **More reliable** than GitHub Actions cron (no delays or skipped runs)
- ✅ **More efficient** (only runs bot when RSS actually changes)
- ✅ **100% free** (Cloudflare free tier: 100k requests/day)
- ✅ **No domain required** (uses Cloudflare Workers cron triggers)

**Setup:** See detailed guide in [`cloudflare-worker/SETUP.md`](cloudflare-worker/SETUP.md)

**Quick Overview:**
1. Create free Cloudflare account
2. Deploy the worker code (`cloudflare-worker/rss-monitor.js`)
3. Configure environment variables (GitHub token, repo, RSS feeds)
4. Add cron trigger (e.g., every 10 minutes)
5. Optionally disable GitHub Actions cron schedule

The worker monitors your RSS feeds and triggers GitHub Actions via `repository_dispatch` only when new content is detected.

---

## 🔧 How It Works

### Social Bot Workflow

#### Option A: GitHub Actions Schedule (Default)

1. **Every 50 minutes**, GitHub Actions triggers the Social Bot
2. **Checks** RSS feed headers (ETag/Last-Modified) for changes
3. **Skips** download if feed unchanged (saves time and bandwidth)

#### Option B: Cloudflare Worker Trigger (Recommended)

1. **Every 10 minutes**, Cloudflare Worker checks RSS feed headers
2. **Only if changed**, triggers GitHub Actions via repository_dispatch

#### Common Workflow (both options)

Once triggered:

1. **Fetches** RSS feeds (only if headers indicate changes)
2. **Filters** entries based on `configuration.json` with the defined `include`/`exclude` rules
3. **Checks** `posted_articles.txt` to avoid duplicates
4. **Downloads** images (if enabled)
5. **Posts** to configured platforms
6. **Submits** to IndexNow for SEO
7. **Updates** `posted_articles.txt` and commits to repository
8. **Triggers** Backup Bot if new posts were detected

### Backup Bot Workflow

Runs when:
- **Triggered** by Social Bot (new post detected)
- **Weekly** every Monday at midnight UTC
- **Manual** workflow dispatch

Process:
1. **Downloads** CSV export (includes all your posts) from Bear Blog
2. **Parses** all published articles
3. **Checks** `processed_articles.txt` for *any* changes (also updates already saved articles with changes)
4. **Creates** folder structure: `YYYY-MM-DD-slug/`
5. **Downloads** all images
6. **Adds** YAML frontmatter with all metadata
7. **Updates** tracking file and commits to repository

---

## 📜 License

This repository is licensed under the [WTFPL](https://www.wtfpl.net/) License.
Feel free to fork and customize for your own blog!

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
