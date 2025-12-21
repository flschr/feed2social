# Cloudflare Worker Setup (optional)

Use a Cloudflare Worker to trigger the Social Bot **only when RSS feeds actually change**.

**Benefits:**
- More reliable than GitHub Actions cron (no delays or skipped runs)
- More efficient (only runs when RSS changes)
- 100% free (Cloudflare free tier with 100k requests/day)

---

## Setup

### 1. Create GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token (classic)"**
3. Name: `RSS Monitor Worker`
4. Scope: **`repo`**
5. Copy the token

### 2. Create Cloudflare Worker

1. Sign up at https://dash.cloudflare.com/sign-up
2. Go to **Workers & Pages** → **Create Worker**
3. Name: `rss-monitor`
4. Click **Deploy**

### 3. Add Worker Code

1. Click **Edit code**
2. Delete all existing code
3. Paste contents from `rss-monitor.js` below
4. Click **Save and Deploy**

### 4. Create KV Namespace

1. Go to **Workers & Pages** → **KV**
2. Click **Create namespace**
3. Name: `RSS_CACHE`

### 5. Configure Environment Variables

In your worker → **Settings** → **Variables**, add:

| Variable | Value |
|----------|-------|
| `GITHUB_TOKEN` | Your GitHub token |
| `GITHUB_OWNER` | Your GitHub username |
| `GITHUB_REPO` | Your GitHub repository name |
| `RSS_FEED_URLS` | Comma-separated feed URLs |

### 6. Bind KV Namespace

In **Settings** → **KV Namespace Bindings**:
- Variable name: `RSS_CACHE`
- Select the `RSS_CACHE` namespace

### 7. Add Cron Trigger

In **Triggers** → **Cron Triggers**:
- Schedule: `*/11 * * * *` (every 1 minutes)

---

## Disable GitHub Actions Cron (Optional)

Once the worker is running, you can disable the Actions schedule:

```yaml
# .github/workflows/social_bot.yml
on:
  # schedule:
  #   - cron: '*/5 * * * *'  # Disabled - using Cloudflare Worker
  workflow_dispatch:
  repository_dispatch:
    types: [rss_feed_update]
```

---

## How It Works

```
Cloudflare Worker (every 1 min)
  ├─ HEAD request to RSS feed
  ├─ Check ETag/Last-Modified headers
  ├─ Compare with KV cache
  │
  ├─ If unchanged: exit
  │
  └─ If changed:
      ├─ Update KV cache
      └─ Trigger GitHub Actions via repository_dispatch
```

---

## Troubleshooting

**Actions don't run:**
- Check `GITHUB_TOKEN` has `repo` scope
- Verify `GITHUB_OWNER` and `GITHUB_REPO` values

**Always reports "changed":**
- Check KV namespace is bound as `RSS_CACHE`
- Some servers don't send ETag headers (expected)

**View logs:**
- Worker → Logs → Begin log stream

---

## Related Documentation

- [Social Bot](SOCIAL_BOT.md) - Automatic social media posting
- [Backup Bot](BACKUP_BOT.md) - Automatic blog backups
- [Feed Configuration](CONFIGURATION.md) - Configure RSS feeds and templates


---
## Paste everything below as Cloudflare Worker code

```
/**
 * Cloudflare Worker: RSS Feed Monitor (`rss-monitor.js`)
 *
 * This worker monitors RSS feeds for changes and triggers GitHub Actions
 * when new content is detected. It uses ETag/Last-Modified headers for
 * efficient change detection.
 *
 * Setup Instructions:
 * 1. Create a new Cloudflare Worker at https://workers.cloudflare.com
 * 2. Copy this code into the worker editor
 * 3. Set the following environment variables in Worker settings:
 *    - GITHUB_TOKEN: Personal Access Token with 'repo' scope
 *    - GITHUB_OWNER: Your GitHub username (e.g., "flschr")
 *    - GITHUB_REPO: Your repository name (e.g., "bearblog-automation")
 *    - RSS_FEED_URLS: Comma-separated list of RSS feed URLs to monitor
 * 4. Add a Cron Trigger
 * 5. Deploy the worker
 */

// Configuration via environment variables
const CONFIG = {
  GITHUB_API: 'https://api.github.com',
  DISPATCH_EVENT_TYPE: 'rss_feed_update',
  REQUEST_TIMEOUT: 10000,
};

/**
 * Main handler for scheduled triggers
 */
export default {
  async scheduled(event, env, ctx) {
    console.log('RSS Monitor: Starting scheduled check');

    try {
      await checkFeeds(env);
    } catch (error) {
      console.error('Error in scheduled handler:', error);
    }
  },

  /**
   * HTTP handler for manual testing
   * Visit worker URL to manually trigger a check
   */
  async fetch(request, env, ctx) {
    if (request.method === 'GET') {
      try {
        const result = await checkFeeds(env);
        return new Response(JSON.stringify(result, null, 2), {
          headers: { 'Content-Type': 'application/json' },
        });
      } catch (error) {
        return new Response(JSON.stringify({ error: error.message }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        });
      }
    }

    return new Response('RSS Feed Monitor - Use GET to test', { status: 200 });
  },
};

/**
 * Check all configured RSS feeds for changes
 */
async function checkFeeds(env) {
  const { GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO, RSS_FEED_URLS } = env;

  // Validate configuration
  if (!GITHUB_TOKEN || !GITHUB_OWNER || !GITHUB_REPO || !RSS_FEED_URLS) {
    throw new Error('Missing required environment variables');
  }

  const feedUrls = RSS_FEED_URLS.split(',').map(url => url.trim());
  const results = {
    checked: [],
    changed: [],
    triggered: false,
    errors: [],
  };

  console.log(`Checking ${feedUrls.length} feed(s)`);

  // Check each feed
  for (const feedUrl of feedUrls) {
    try {
      const hasChanged = await checkFeedChanged(feedUrl, env);

      results.checked.push(feedUrl);

      if (hasChanged) {
        console.log(`Feed changed: ${feedUrl}`);
        results.changed.push(feedUrl);
      } else {
        console.log(`Feed unchanged: ${feedUrl}`);
      }
    } catch (error) {
      console.error(`Error checking feed ${feedUrl}:`, error);
      results.errors.push({ feed: feedUrl, error: error.message });
    }
  }

  // If any feed changed, trigger GitHub Actions
  if (results.changed.length > 0) {
    try {
      await triggerGitHubActions(GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO, results.changed);
      results.triggered = true;
      console.log('GitHub Actions triggered successfully');
    } catch (error) {
      console.error('Error triggering GitHub Actions:', error);
      results.errors.push({ action: 'trigger', error: error.message });
    }
  }

  return results;
}

/**
 * Check if a feed has changed using HEAD request and KV storage
 */
async function checkFeedChanged(feedUrl, env) {
  try {
    // Make HEAD request to get headers
    const response = await fetch(feedUrl, {
      method: 'HEAD',
      headers: {
        'User-Agent': 'RSS-Monitor/1.0',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const newETag = response.headers.get('etag') || '';
    const newLastModified = response.headers.get('last-modified') || '';

    // Get cached headers from KV storage
    const cacheKey = `feed:${feedUrl}`;
    const cachedData = await env.RSS_CACHE?.get(cacheKey, { type: 'json' });

    // If no cache, assume changed and store new headers
    if (!cachedData) {
      await env.RSS_CACHE?.put(cacheKey, JSON.stringify({
        etag: newETag,
        lastModified: newLastModified,
        lastCheck: new Date().toISOString(),
      }));
      return true; // First check, assume changed
    }

    // Compare ETag (more reliable)
    if (newETag && cachedData.etag) {
      if (newETag === cachedData.etag) {
        return false; // No change
      }
    }

    // Compare Last-Modified
    if (newLastModified && cachedData.lastModified) {
      if (newLastModified === cachedData.lastModified) {
        return false; // No change
      }
    }

    // Headers differ or missing - assume changed
    await env.RSS_CACHE?.put(cacheKey, JSON.stringify({
      etag: newETag,
      lastModified: newLastModified,
      lastCheck: new Date().toISOString(),
    }));

    return true;
  } catch (error) {
    console.error(`Error checking feed ${feedUrl}:`, error);
    // On error, assume changed to avoid missing updates
    return true;
  }
}

/**
 * Trigger GitHub Actions via repository_dispatch
 */
async function triggerGitHubActions(token, owner, repo, changedFeeds) {
  const url = `${CONFIG.GITHUB_API}/repos/${owner}/${repo}/dispatches`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Accept': 'application/vnd.github+json',
      'User-Agent': 'RSS-Monitor/1.0',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      event_type: CONFIG.DISPATCH_EVENT_TYPE,
      client_payload: {
        feeds: changedFeeds,
        triggered_at: new Date().toISOString(),
      },
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`GitHub API error: ${response.status} - ${errorText}`);
  }

  return true;
}
```
