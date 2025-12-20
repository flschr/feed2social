---
uid: "chMPbgCyCRufCPKYwbko"
title: "🐻 A Markdown Toolbar for lazy Bear Blog users"
slug: "a-markdown-toolbar-for-lazy-bear-blog-users"
alias: ""
published_date: "2025-12-19T22:01:00+00:00"
all_tags: "[\"bearblog\", \"blog\", \"coding\", \"plugins\"]"
publish: "True"
make_discoverable: "True"
is_page: "False"
canonical_url: ""
meta_description: ""
meta_image: "https://bear-images.sfo2.cdn.digitaloceanspaces.com/fischr/1766177197947.webp"
lang: "en"
class_name: ""
first_published_at: "2025-12-19T22:01:00+00:00"
---

There is one thing that I really miss in Bear Blog, and this is a somewhat more powerful editor. Don't get me wrong, I love Markdown but I’m also lazy. I definitely don't want to type out links and formatting codes manually every single time, like a monkey.

Since Bear Blog allows custom Javascript in the dashboard, I knew I could create a plugin to solve my pains. But being lazy, I looked around first and found two existing plugins that seemed to be exactly what I needed.

The [first one](https://github.com/HermanMartinus/bear-plugins?tab=readme-ov-file#syntax-highlighting-and-formatting-controls-in-editor-wip) was from Herman (the creator of Bear Blog), embedding [Overtype](https://overtype.dev/). It adds beautiful syntax highlighting, but unfortunately, it broke the image uploading functionality for me. With the [other plugin](https://streetsofchance.bearblog.dev/add-a-style-widget-and-markdown-prettifier-to-your-bear-blog-with-easymde/) uploads worked, but the editor felt unstable and somewhat "meh" in daily use.

## A toolbar that just works

So I decided to build my own Markdown toolbar, and as sharing is caring, I’m making it available to the community.

![Screenshot of the Bear Blog editor with a Markdown toolbar (B, I, H1, H2, etc.) and the Text „This fancy markdown toolbar is very useful“, with the word „useful“ being marked blue.](https://bear-images.sfo2.cdn.digitaloceanspaces.com/fischr/1766177197947.webp)

It’s not a reinvention of the wheel, it’s a Markdown toolbar, after all. But besides the usual features, it offers a few specific improvements.

- It doesn’t break the media uploader, it even adds a *dedicated upload button* to the menu bar.
- If you have a URL in your clipboard, the link button recognizes it and formats the Markdown code *automatically*.
- A built-in *character counter* turns red once you pass 300 characters, just in case you want to cross-post your full article to Mastodon or Bluesky and prevent that it got cut off.
- And it "cleans" the footer below the editor, to give the editor some more room on the page.

In the settings, you can toggle an *Advanced Mode* for even more features. This adds specialized buttons for info and warning boxes (you'll need to add [this CSS](https://thecommabandit.bearblog.dev/cohost-infoboxes/) to your site for them to style correctly). It also includes a rating button that quickly inserts stars (★★★☆☆) into your book, movie, or restaurant reviews.

## Get this toolbar for your Bear Blog

To use this toolbar, simply add the code below to *Dashboard > Settings > Footer content* in your Bear Blog.

```
<script src="https://cdn.jsdelivr.net/gh/flschr/bearblog-plugins@main/bear/markdown-toolbar_basic.js"></script>

```


And the really cool thing is, this works in any web browser, whether you’re on a notebook, tablet, or smartphone.

---

This plugin currently serves all my needs perfectly. However, if you have ideas for features or want to contribute, I'd love to hear from you! Feel free to catch me on [Mastodon](https://mastodon.social/@fischr).