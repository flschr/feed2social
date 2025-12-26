---
uid: chMPbgCyCRufCPKYwbko
title: 🐻 Markdown Power-Editor for Bear Blog
slug: markdown-power-editor-for-bear-blog
alias: the-markdown-toolbar-plugin-for-lazy-bear-blog-users
published_date: "2025-12-19T22:01:00+00:00"
all_tags: "[\"bearblog\", \"blog\", \"coding\", \"plugins\"]"
publish: "True"
make_discoverable: "True"
is_page: "False"
canonical_url: ""
meta_description: ""
meta_image: "https://bear-images.sfo2.cdn.digitaloceanspaces.com/fischr/001.webp"
lang: ""
class_name: ""
first_published_at: "2025-12-19T22:01:00+00:00"
---

> #### Version 2 is here!
> I’ve completely rebuilt it from the ground up, turning a simple set of buttons into a professional Markdown editor for Bear Blog. If you’re using the old version, I highly recommend switching to the new script link below to unlock the full potential.

![A graphic showcasing a digital document editor on a computer screen, with a vibrant turquoise background. The text features the title "Bear Blog - Markdown Plugin Walkthrough," emphasizing smarter and easier writing, along with highlights of the content.](https://bear-images.sfo2.cdn.digitaloceanspaces.com/fischr/001.webp)

There is one thing that I really miss in Bear Blog, and this is a more powerful editor. Don't get me wrong, I love Markdown, but I’m also lazy. I definitely don't want to type out links and formatting codes manually every single time, like a monkey.

Since Bear Blog allows custom Javascript in the dashboard, I knew I could create a plugin to solve my pains. But being lazy, I looked around first and found two existing plugins that seemed to be exactly what I needed.

The [first one](https://github.com/HermanMartinus/bear-plugins?tab=readme-ov-file#syntax-highlighting-and-formatting-controls-in-editor-wip) was from Herman (the creator of Bear Blog), embedding [Overtype](https://overtype.dev/). It adds beautiful syntax highlighting, but unfortunately, it broke the image uploading functionality for me. With the [other plugin](https://streetsofchance.bearblog.dev/add-a-style-widget-and-markdown-prettifier-to-your-bear-blog-with-easymde/), uploads worked, but the editor felt unstable and somewhat "meh" in daily use.

## From a simple Toolbar to a powerful Editor

So I decided to build my own Markdown toolbar, and while doing so, the project grew with my wishes and now has become a truly powerful Markdown editor for Bear Blog. As sharing is caring, I’m making it available to the community.

I wasn't trying to reinvent the wheel, just make it spin a lot smoother for people like us. If you want to see the new editor in action, I’ve created a quick walkthrough video showing you how it works and how to set it up. Or, if you prefer reading, you can find the breakdown of features right below.

<iframe width="560" height="315" src="https://www.youtube-nocookie.com/embed/noF461kvZcc?si=8f-QjsC3gFs9KttV" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>

### Essential features for everyone

- Quick buttons for Bold, Italic, Strike-through, Highlights, Inline Code, and H1-H3 Headings.
- Dedicated buttons for bullet/numbered lists, quotes, footnotes, horizontal rules, tables, and code blocks.
- Buttons for [GitHub-style admonitions](/better-admonitions-for-bear-blog/) to easily add Info, Warning, and Caution boxes.

### Smart features to save you clicks

- The image upload button opens the native Bear media uploader and also detects image URLs in your clipboard to offer instant Markdown image formatting.
- The link button automatically detects URLs in your clipboard and links your selected text with a single click.
- Inline preview shows the preview of your post without leaving the editor page. The preview automatically saves the article to ensure you always see the most recent version of the article.
- Native buttons for quick undo & redo, especially helpful on mobile devices.

### Optional power user features

- Full-screen mode for a distraction-free writing experience.
- OpenAI integration to automatically generate image descriptions (ALT-text) from a Markdown image tag. This feature requires your own API-key.
- Define your custom button with any text or code snippet that gets inserted with a click of a button.
- Character counter that shows how many characters you already typed.

The best thing is, you decide which buttons you see. The new settings panel allows you to configure your individual toolbar and toggle buttons and settings on and off.


> #### How the AI-powered alt-text generation works
>  This feature uses the OpenAI gpt-4o-mini model to analyze your images via their URL. It’s designed to be fast, privacy-conscious (data is only sent when you click the button), and extremely cost-efficient, generating descriptions for about 1,000 images costs roughly $1.00. For more details, read the [documentation](https://github.com/flschr/bearblog-plugins?tab=readme-ov-file#ai-alt-text-feature-optional) on GitHub.

## Get this toolbar for your Bear Blog

To use this toolbar, simply add the code below to *Dashboard > Settings > Footer content* in your Bear Blog.

```
<script src="https://cdn.jsdelivr.net/gh/flschr/bearblog-plugins@stable/bear/markdown-toolbar.js"></script>

```
And the really cool thing is, this works in any web browser, whether you’re on a notebook, tablet, or smartphone.

> ##### Note on the Legacy Version
> The [original toolbar](https://github.com/flschr/bearblog-plugins/blob/main/bear/markdown-toolbar_basic.js) isn't going anywhere and will stay available for those who want to keep their current setup. To enjoy the new features, you'll need to manually switch to the new version provided in this article.

---

The source code of the Markdown toolbar is available in this [GitHub repository](https://github.com/flschr/bearblog-plugins).

If you want to report a bug, have ideas for great features, or just want to say thank you, I'd love to hear from you! Feel free to catch me on [Mastodon](https://mastodon.social/@fischr).