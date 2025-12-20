# 🐻🚀 Bear Blog automation for fischr.org

A complete automation suite for Bear Blog (and other RSS-based blogs). This repository handles **Social Media Distribution**, **SEO Indexing**, and **Automated Backups** to Backblaze B2.

## 📂 Project Structure

* `feed2social/`: The heart of the bot. Handles RSS monitoring, BlueSky/Mastodon posting, and IndexNow pings.
* `backup/`: Scripts for incremental and full backups of your blog content and images.
* `posted.txt`: The "memory" of the bot, ensuring no article is processed twice. This file stays in the root directory.

---

## ✨ Features

1.  **Smart Social Sharing**: Automatically posts new articles to **BlueSky** and **Mastodon** based on your rules. You can create as many rules for as many feeds as you need, with flexible include and exclude filters.
2.  **Media Support & Accessibility**: Automatically uploads the first image from your post as a native attachment, including **ALT-text** for accessibility.
3.  **SEO Automation**: Pings **IndexNow** (Bing, Yandex, etc.) immediately after a new post is detected.
4.  **Automated Backups**: Converts posts to clean Markdown and stores them along with all images in a **Backblaze B2** bucket, maintaining a chronological folder structure.

---

## 🛠 Setup Guide for Forking

Follow these steps to set up this suite for your own blog:

### 1. Fork this Repository
Click the **Fork** button at the top right of this page to create your own copy.

### 2. Configure your Blog
Edit `feed2social/config.json` to match your blog's details. You can add multiple configuration blocks for different feeds.

```json
[
  {
    "name": "My Blog",
    "url": "https://yourblog.com/feed/",
    "include": ["Announcement"], 
    "exclude": ["Draft"],
    "include_images": true,
    "targets": ["bluesky", "mastodon"],
    "template": "🚀 New Post: {title}\n\n{link}"
  }
]
```

#### Configuration Options:

| Option | Description |
| :--- | :--- |
| **`name`** | A descriptive name for the feed (used for logging). |
| **`url`** | The direct link to your RSS feed. |
| **`include`** | *(Optional)* Only posts containing these keywords in the **title** or **hashtags** will be shared. |
| **`exclude`** | *(Optional)* Posts containing these keywords in the **title** or **hashtags** will be ignored. |
| **`include_images`** | If `true`, the bot attaches the first image of your post (including ALT-text). Photo posts will automatically add the full content of the artilce to imiate a native Mastodon and Bluesky post. Content longer than 300 (Bluesky) and 500 (Mastodon) characters automatically gets cut off. |
| **`targets`** | List of platforms to post to (`"bluesky"`, `"mastodon"`). |
| **`template`** | Your post format. Use placeholders: `{title}`, `{link}`, `{content}`. |

### 3. Set up SEO & Backups (Optional)

#### IndexNow (SEO)
To automate indexing for Bing and others:
1.  Generate an API Key at [IndexNow.org](https://www.indexnow.org/how-to).
2.  Host the key as a `.txt` file or via a DNS TXT record (recommended for Bearblog).
3.  Add the key to your GitHub Secrets as `INDEXNOW_KEY`.

#### Backblaze B2 (Backups)
1.  Create a bucket in **Backblaze B2**.
2.  Set Lifecycle Rules to "Keep only the last version" to save space.

### 4. Configure GitHub Secrets & Variables
Go to `Settings > Secrets and variables > Actions` and add the following:

| Secret / Variable | Description |
| :--- | :--- |
| `RSS_FEED_URL` | **Required.** The URL of your RSS feed (e.g. `https://yourblog.com/feed/`) |
| `BSKY_HANDLE` | Your BlueSky handle (e.g., `user.bsky.social`) |
| `BSKY_PW` | BlueSky **App Password** |
| `MASTO_TOKEN` | Mastodon Access Token |
| `INDEXNOW_KEY` | Your IndexNow API Key |
| `B2_KEY_ID` | Backblaze B2 Key ID |
| `B2_APPLICATION_KEY` | Backblaze B2 Application Key |
| `B2_BUCKET_NAME` | The name of your B2 Bucket |

### 5. Enable Actions
Go to the **Actions** tab and click **"I understand my workflows, go ahead and enable them"**.

---

## 🤖 How it works (Technical)

The system uses **GitHub Actions** to run on a schedule (every 6 minutes for the bot, every 6 hours for backups).

1.  **Scanning**: Parses your RSS feed via `feedparser`.
2.  **Deduplication**: Compares entries against `posted.txt`.
3.  **Processing**: Downloads images, extracts ALT-text, converts HTML to Markdown, and removes unwanted tags (like Bearblog's "pot-of-honey").
4.  **Execution**: Dispatches data to Social Media APIs, IndexNow, and Backblaze B2.
5.  **State Save**: Commits the updated `posted.txt` back to the repository.

*Note: The `backup/full_backup.py` script is intended for one-time manual runs to archive your entire blog history. It may require minor manual path adjustments.*

---

## Author
Created by **[René Fischer](https://fischr.org)**.

## 📝 License
MIT - Feel free to use it for your own blog!
