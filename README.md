# (Bear) Blog Automation for fischr.org

Hey and welcome 👋🏼 This is the powerhouse behind my [Bear Blog](https://bearblog.dev)-powered website [fischr.org](https://fischr.org). Whenever I publish a new article, this repository automatically

- **posts the article to Mastodon and Bluesky**, with a individual template based on the content of the article
- **backs up everything** (new or changed) as Markdown files with images right here in this repo
- and **pings search engines** for faster indexing.

If you are running a Bear Blog (or any blog with an RSS feed) and want similar automation, feel free to fork this repo and adapt it to your needs. Read on to see how it works!

---

## How It Works

The automation runs via GitHub Actions and is triggered in two ways:

1. **Scheduled**: Checks for new posts in configured intervalls
2. **Webhook** *(optional)*: Instant trigger via Cloudflare Worker when a new post is published

When a new article is detected in the RSS feed, the bots spring into action, posting to social media, creating backups, and pinging search engines.

## Fork & Set Up Your Own

Want to use this for your blog? Here is how:

### 1. Fork this repo & edit `config.yaml`

```yaml
blog:
  bearblog_username: "your-username"

backup:
  folder: "blog-backup"  # Customize your backup folder name

social:
  mastodon_instance: "https://mastodon.social"
```

### 2. Configure your feeds

Edit `bots/social_bot/config.json` to point to your RSS feeds. See the [Social Bot documentation](docs/SOCIAL_BOT.md) for details.

### 3. Add GitHub Secrets

Go to **Settings → Secrets → Actions** and add:

| Secret | Required | Description |
|--------|----------|-------------|
| `BSKY_HANDLE` | Yes | Your BlueSky handle (e.g., `user.bsky.social`) |
| `BSKY_PW` | Yes | BlueSky App Password |
| `MASTO_TOKEN` | Yes | Mastodon Access Token |
| `INDEXNOW_KEY` | No | IndexNow API key for SEO pings |
| `BEAR_COOKIE` | No | `sessionid=...` cookie for backup bot |

### 4. Enable GitHub Actions

Go to the **Actions** tab and enable workflows. Done!

## Project Structure

```
├── config.yaml           # Central configuration
├── bots/
│   ├── social_bot/       # Social media posting
│   │   ├── config.json   # Feed & template config
│   │   └── cloudflare-worker/
│   └── backup_bot/       # Markdown backup bot
├── blog-backup/          # Archived posts (auto-generated, customizable)
└── docs/                 # Documentation
```

## Documentation

- [Social Bot](docs/SOCIAL_BOT.md) - Automatic social media posting & feed configuration
- [Backup Bot](docs/BACKUP_BOT.md) - Automatic blog backups
- [Cloudflare Worker](docs/CLOUDFLARE_WORKER.md) - Instant trigger setup *(optional)*

## License

[WTFPL](https://www.wtfpl.net/) — Do what you want.

---

Made by [René Fischer](https://fischr.org) to automate [fischr.org](https://fischr.org).
