# feed2social

This bot periodically checks RSS feeds and automatically posts new entries to social networks like BlueSky and Mastodon. Additionally, the URL of the new post is submitted to search engines via IndexNow.

## How it works

The bot is controlled by a GitHub Action (see `.github/workflows/main.yml`), which runs by default every 6 minutes.

1.  The bot loads the RSS feeds defined in `config.json`.
2.  It checks which posts are already listed in `posted.txt` to avoid duplicates.
3.  For each new post, it checks if it matches the filter criteria (`include`/`exclude`).
4.  Matching posts are formatted according to the `template`.
5.  The formatted post is sent to the defined `targets` like BlueSky and Mastodon.
6.  Optionally, the first image from the post is extracted and sent along.
7.  The post's URL is submitted to the IndexNow service (Bing, Yandex, etc.).
8.  The `posted.txt` file is updated with the new URL and pushed back to the repository to save the state.

## Setup

To use the bot for your own purposes, follow these steps:

### 1. Fork the repository

Create a fork of this repository in your own GitHub account.

### 2. Customize `config.json`

The `config.json` is the main configuration file. It contains an array of feed objects, each defining a source.

**Example `config.json`:**
```json
[
  {
    "name": "My Blog",
    "url": "https://my-blog.com/rss.xml",
    "include": ["Announcement", "Release"],
    "exclude": ["Private"],
    "include_images": true,
    "targets": ["bluesky", "mastodon"],
    "template": "New blog post: {title}\n\n{link}"
  }
]
```

*   `name`: Ein beliebiger Name für den Feed (wird in den Logs verwendet).
*   `url`: Die URL des RSS-Feeds.
*   `include` (optional): Eine Liste von Keywords. Ein Beitrag wird nur gepostet, wenn mindestens eines dieser Wörter im Titel oder in der Zusammenfassung vorkommt.
*   `exclude` (optional): Eine Liste von Keywords. Ein Beitrag wird ignoriert, wenn eines dieser Wörter im Titel oder in der Zusammenfassung vorkommt.
*   `include_images`: Wenn `true`, versucht der Bot, das erste Bild aus dem Beitrag zu extrahieren und mitzuposten.
*   `targets`: Eine Liste der Plattformen, auf denen gepostet werden soll. Unterstützt werden `"bluesky"` und `"mastodon"`.
*   `template`: Eine Vorlage für den Post-Text. Verfügbare Platzhalter sind `{title}`, `{link}` und `{content}` (der Textinhalt des Beitrags).

### 3. GitHub Secrets einrichten

Damit der Bot posten kann, müssen Sie die entsprechenden Zugangsdaten als "Repository Secrets" in Ihrem Fork hinterlegen. Gehen Sie dazu in Ihrem GitHub-Repository auf `Settings > Secrets and variables > Actions`.

Folgende Secrets werden benötigt:

*   `BSKY_HANDLE`: Ihr BlueSky-Benutzername (z.B. `example.bsky.social`).
*   `BSKY_PW`: Ein App-Passwort für BlueSky (**nicht** Ihr reguläres Passwort). Sie können dies in den BlueSky-Einstellungen unter "App-Passwörter" erstellen.
*   `MASTO_TOKEN`: Ihr Mastodon-Zugangstoken. Sie können diesen in den Mastodon-Einstellungen unter `Entwicklung > Neuer Anwendungsfall` erstellen.
*   `INDEXNOW_KEY` (optional): Ihr Schlüssel für den IndexNow-Dienst. Wenn Sie diesen nicht benötigen, können Sie die Funktion `submit_to_indexnow` in `bot.py` auskommentieren.

Nachdem Sie alles eingerichtet haben, wird die GitHub Action automatisch ausgeführt und beginnt mit dem Posten Ihrer Feed-Inhalte. Sie können die Ausführung auch manuell über den "Workflow Dispatch"-Button im Actions-Tab starten.
