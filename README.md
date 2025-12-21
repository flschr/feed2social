# 🐻 (Bear) Blog Automation for fischr.org

Hey and welcome 👋🏼 This is the powerhouse behind my [Bear Blog](https://bearblog.dev)-powered website [fischr.org](https://fischr.org). Whenever I publish a new article, this repository automatically

- **posts the article to Mastodon and Bluesky**, with an individual template based on the content
- **backs up everything** as Markdown files with images right here in this repo
- and **pings search engines** for faster indexing.

## Project Structure

```
├── config.yaml              # Central configuration
├── bots/
│   ├── social_bot/          # Social media posting bot
│   │   └── config.json      # Feed & template config
│   └── backup_bot/          # Bear Blog backup bot
├── blog-backup/             # Archived posts (auto-generated)
└── docs/                    # Documentation
```

## Setup your own (Bear) Blog Automation

Want to use this for your blog? Here's the path:

1. **Fork this repo**
2. **Read [Social Bot](docs/SOCIAL_BOT.md)** → Configure feeds, templates & secrets for your social media posts
3. **Read [Backup Bot](docs/BACKUP_BOT.md)** → Set up automatic Bear Blog backups *(optional)*
4. **Read [Cloudflare Worker](docs/CLOUDFLARE_WORKER.md)** — Issue social media posts instantly (<1 minute delay) *(optional)*

## Author & License

Made by [René Fischer](https://fischr.org) to automate [fischr.org](https://fischr.org).
License: [WTFPL](https://www.wtfpl.net/) — Do what you want. I couldn't care less :)

