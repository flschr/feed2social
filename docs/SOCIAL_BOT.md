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

Each feed is configured as an object in the JSON array:

```json
[
  {
    "name": "Blog Articles",
    "url": "https://yourblog.com/feed/",
    "include": ["blog"],
    "exclude": ["draft"],
    "include_images": true,
    "template": "New post: {title}\n\n{link}",
    "targets": ["bluesky", "mastodon"]
  }
]
```

#### Configuration Options

| Option | Required | Description |
|--------|----------|-------------|
| `name` | Yes | Descriptive name (used in logs) |
| `url` | Yes | RSS feed URL |
| `include` | No | Only posts with these keywords in title/hashtags/categories |
| `exclude` | No | Skip posts with these keywords |
| `include_images` | No | Attach first image with ALT text (`true`/`false`) |
| `template` | Yes | Post format with placeholders |
| `targets` | Yes | Platforms: `["bluesky"]`, `["mastodon"]`, or both |

#### Template Variables

Use these placeholders in the `template` field:

| Variable | Description |
|----------|-------------|
| `{title}` | Post title |
| `{link}` | URL to the blog post |
| `{content}` | Cleaned text content (auto-truncated) |

**Content limits:**
- BlueSky: 300 characters
- Mastodon: 500 characters

**Hashtags:** Added in templates are automatically converted to native rich text on BlueSky.

#### Examples

**Photo Posts**
```json
{
  "name": "Photos",
  "url": "https://yourblog.com/feed?q=photos",
  "include": ["photo"],
  "include_images": true,
  "template": "{content} #photography",
  "targets": ["bluesky", "mastodon"]
}
```

**Blog Articles**
```json
{
  "name": "Blog",
  "url": "https://yourblog.com/feed/",
  "include": ["blog"],
  "exclude": ["draft", "private"],
  "template": "New post: {title}\n\n{link}",
  "targets": ["bluesky", "mastodon"]
}
```

**Movie Reviews**
```json
{
  "name": "Movies",
  "url": "https://yourblog.com/feed?q=movies",
  "template": "Just watched {title}. {link}",
  "targets": ["bluesky"]
}
```

---

## GitHub Secrets

Configure these in **Settings → Secrets → Actions**:

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

### Automatic Issue for Unmatched Articles
When a new article doesn't match any posting configuration, the bot:
1. Generates a detailed matching report showing:
   - Article info (title, link, published date)
   - Detected RSS tags from the feed
   - Each config checked and why it didn't match
2. Creates a GitHub Issue with the full report
3. Suggests possible actions to fix the configuration

This helps diagnose why articles aren't being posted and makes it easier to adjust the filter rules.

---

## Triggering

The bot can be triggered:
- **Manually**: GitHub Actions → Run workflow
- **Webhook**: Via Cloudflare Worker (see [Cloudflare Worker Setup](CLOUDFLARE_WORKER.md))
- **Schedule**: Uncomment cron in workflow file

---

## Related Documentation

- [Backup Bot](BACKUP_BOT.md) - Automatic blog backups
- [Cloudflare Worker](CLOUDFLARE_WORKER.md) - Instant trigger setup
