# fischr.org automations

This repository contains a few scripts and Github actions to automate posting content on my social media accounts and to backup my website to Backblaze. 

The bot periodically checks RSS feeds and automatically posts new entries to social networks like BlueSky and Mastodon. Additionally, it submits new post URLs to search engines via the IndexNow service.

The backup is backing new articles up to Backblaze (B2) with every new feed entry. There is also a full backup script, just in case I want to do a full backup.

## How it works

The bot is powered by a GitHub Action (see `.github/workflows/main.yml`), which runs every 6 minutes by default.

1.  **Load Feeds**: The bot loads the RSS feeds defined in `config.json`.
2.  **Duplicate Check**: It compares entries against `posted.txt` to avoid double-posting.
3.  **Filter**: It checks if a post matches your `include` or `exclude` criteria.
4.  **Format**: Posts are formatted using your custom `template` defined in the configuration.
5.  **Dispatch**: The formatted content is sent to your defined `targets` like BlueSky or Mastodon.
6.  **Media**: If enabled, the bot extracts the first image and attaches it to the post.
7.  **Indexing**: The post URL is submitted to the IndexNow service for Bing, Yandex, and others.
8.  **Sync**: The `posted.txt` file is updated and pushed back to your repository to save the state.

## Setup

Follow these steps to set up the bot for your own feeds:

### 1. Fork the repository
Create a fork of this repository in your own GitHub account.

### 2. Customize `config.json`
This is your main configuration file. It contains an array of feed objects.

**Example `config.json`:**
```json
[
  {
    "name": "My Blog",
    "url": "[https://fischr.org/feed/](https://fischr.org/feed/)",
    "include": ["Announcement", "Release"],
    "exclude": ["Private"],
    "include_images": true,
    "targets": ["bluesky", "mastodon"],
    "template": "New blog post: {title}\n\n{link}"
  }
]
```

*   `name`: A descriptive name for the feed used in logs.
*   `url`: The URL of the RSS feed.
*   `include` (optional): A list of keywords; a post is only shared if it contains at least one of these words.
*   `exclude` (optional): A list of keywords; a post is ignored if it contains any of these words.
*   `include_images`: If `true`, the bot tries to extract and post the first image from the article.
*   `targets`: The platforms to post to, supporting `"bluesky"` and `"mastodon"`.
*   `template`: The post text format using placeholders like `{title}`, `{link}` and `{content}`

### 3. Configure GitHub Secrets

To allow the bot to post, you must add your credentials as Repository Secrets under `Settings > Secrets and variables > Actions`.

Required Secrets:

* `BSKY_HANDLE`: Your BlueSky identifier without the @.
* `BSKY_PW`: An App Password created in BlueSky Settings.
* `MASTO_TOKEN`: Your Mastodon access token created under Development settings.
* `INDEXNOW_KEY`: (optional) your IndexNow API key, which can be verified via a DNS TXT record named _indexnow.
