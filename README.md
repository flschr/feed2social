# 🚀 bearblog automation for fischr.org

A complete automation suite for Bearblog (and other RSS-based blogs). This repository handles **Social Media Distribution**, **SEO Indexing**, and **Automated Backups** to Backblaze B2.

## 📂 Project Structure

* `feed2social/`: The heart of the bot. Handles RSS monitoring, BlueSky/Mastodon posting, and IndexNow pings.
* `backup/`: Scripts for incremental and full backups of your blog content and images.
* `posted.txt`: The "memory" of the bot, ensuring no article is processed twice. This file stays in the root directory.

---

## ✨ Features

1.  **Smart Social Sharing**: Automatically posts new articles to **BlueSky** and **Mastodon** based on your rules. You can create as many rules for as many feeds as you need, with flexible include and exclude filters to automate posting of your content.
2.  **Media Support for Mastodon & Bluesky**: Social sharing allows to upload the first image from your post directly to Mastodon & Bluesky to use it as a native attachment on the platforms, including the ALT-text for accessibility.
3.  **SEO Automation**: Pings **IndexNow** (Bing, Yandex, etc.) immediately after a new post is detected.
4.  **Full & Incremental Backups**: Converts posts to clean Markdown and stores them along with all images in a **Backblaze B2** bucket.

---

## 🛠 Setup Guide for Forking

If you want to use this suite for your own blog, follow these steps:

### 1. Fork this Repository
Click the **Fork** button at the top right of this page to create your own copy.

### 2. Configure your Blog
Edit `feed2social/config.json` to match your blog's details:

```json
[
  {
    "name": "My Awesome Blog",
    "url": "[https://yourblog.com/feed/](https://yourblog.com/feed/)",
    "include_images": true,
    "targets": ["bluesky", "mastodon"],
    "template": "Check out my new post: {title}\n\n{link}"
  }
]
```

### 3. Set up Backblaze B2 (optional)
If you want to use the backup feature:
* Create a bucket in **Backblaze B2**.
* Set Lifecycle Rules to "Keep only the last version" to save space.

### 4. Configure GitHub Secrets
Go to `Settings > Secrets and variables > Actions` in your forked repo and add the following:

| Secret | Description |
| :--- | :--- |
| `BSKY_HANDLE` | Your BlueSky handle (e.g., `user.bsky.social`) |
| `BSKY_PW` | BlueSky **App Password** |
| `MASTO_TOKEN` | Mastodon Access Token |
| `INDEXNOW_KEY` | Your IndexNow API Key (optional) |
| `B2_KEY_ID` | Backblaze B2 Key ID |
| `B2_APPLICATION_KEY` | Backblaze B2 Application Key |
| `B2_BUCKET_NAME` | The name of your B2 Bucket |

### 5. Enable Actions
Go to the **Actions** tab in your repository and click **"I understand my workflows, go ahead and enable them"**.

---

## 🤖 How it works (Technical)

The system uses **GitHub Actions** to run on a schedule (by default, every 6 minutes for the bot, every 6 hours for regular backups).

1.  **Scanning**: It parses your RSS feed via `feedparser`.
2.  **Deduplication**: It checks `posted.txt`. If the link was already posted, it skips.
3.  **Processing**: It downloads images, converts HTML to Markdown, and cleans it up.
4.  **Execution**: It sends data to Social Media APIs, IndexNow, and Backblaze B2.
5.  **State Save**: It commits the updated `posted.txt` back to the repository.

---

## Author
Created by **[René Fischer](https://fischr.org)**.

## 📝 License
MIT - Feel free to use it for your own blog!