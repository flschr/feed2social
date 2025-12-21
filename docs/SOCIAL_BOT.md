# Social Bot

The Social Bot automatically posts new blog entries from your RSS feeds to Bluesky and Mastodon.

---

## How It Works

1. Monitors your configured RSS feeds
2. Detects new posts using ETag/Last-Modified headers
3. Filters posts based on include/exclude rules
4. Formats posts using customizable templates
5. Posts to Bluesky and/or Mastodon with rich text and link cards
6. Submits URLs to search engines via IndexNow

---

## Configuration

### Central Config (`config.yaml`)

```yaml
social:
  mastodon_instance: "https://mastodon.social"
```

### Feed Config (`bots/social_bot/config.json`)

See [Feed Configuration](CONFIGURATION.md) for detailed setup.

---

## GitHub Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `BSKY_HANDLE` | Yes | Your BlueSky handle (e.g., `user.bsky.social`) |
| `BSKY_PW` | Yes | BlueSky App Password |
| `MASTO_TOKEN` | Yes | Mastodon Access Token |
| `INDEXNOW_KEY` | No | IndexNow API key for SEO pings |

### Getting Credentials

**BlueSky App Password:**
1. Go to [bsky.app/settings/app-passwords](https://bsky.app/settings/app-passwords)
2. Create a new app password
3. Copy and save as `BSKY_PW`

**Mastodon Access Token:**
1. Go to your instance → Settings → Development
2. Create a new application
3. Copy the access token as `MASTO_TOKEN`

---

## Features

### Rich Text Support
- Hashtags are converted to clickable tags
- Links get proper rich text formatting
- Bluesky posts include link card previews with OG images (handled automatically by Mastodon)

### Smart Filtering
- Include/exclude posts by keywords in title, hashtags/categories
- Attach first image with ALT text (optional)

### Efficiency
- Tracks posted articles to prevent duplicates

---

## Triggering

The bot can be triggered:
- **Manually**: GitHub Actions → Run workflow
- **Webhook**: Via Cloudflare Worker (see [Cloudflare Worker Setup](CLOUDFLARE_WORKER.md))
- **Schedule**: Uncomment cron in workflow file

---

## Related Documentation

- [Backup Bot](BACKUP_BOT.md) - Automatic blog backups
- [Feed Configuration](CONFIGURATION.md) - Configure RSS feeds and templates
- [Cloudflare Worker](CLOUDFLARE_WORKER.md) - Instant trigger setup
