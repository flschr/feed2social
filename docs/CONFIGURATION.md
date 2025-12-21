# Feed Configuration Guide

This guide explains how to configure the Social Bot to post from your RSS feeds.

---

## Feed Configuration (`bots/social_bot/config.json`)

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

---

## Configuration Options

| Option | Required | Description |
|--------|----------|-------------|
| `name` | Yes | Descriptive name (used in logs) |
| `url` | Yes | RSS feed URL |
| `include` | No | Only posts with these keywords in title/hashtags/categories |
| `exclude` | No | Skip posts with these keywords |
| `include_images` | No | Attach first image with ALT text (`true`/`false`) |
| `template` | Yes | Post format with placeholders |
| `targets` | Yes | Platforms: `["bluesky"]`, `["mastodon"]`, or both |

---

## Template Variables

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

---

## Examples

### Photo Posts
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

### Blog Articles
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

### Movie Reviews
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

### Required

| Secret | Description |
|--------|-------------|
| `BSKY_HANDLE` | Your BlueSky handle (e.g., `user.bsky.social`) |
| `BSKY_PW` | BlueSky **App Password** ([create here](https://bsky.app/settings/app-passwords)) |
| `MASTO_TOKEN` | Mastodon Access Token (Settings → Development → New Application) |

### Optional

| Secret | Description |
|--------|-------------|
| `INDEXNOW_KEY` | API key from [indexnow.org](https://www.indexnow.org) for SEO |

---

## Related Documentation

- [Social Bot](SOCIAL_BOT.md) - Automatic social media posting
- [Backup Bot](BACKUP_BOT.md) - Automatic blog backups
- [Cloudflare Worker](CLOUDFLARE_WORKER.md) - Instant trigger setup
