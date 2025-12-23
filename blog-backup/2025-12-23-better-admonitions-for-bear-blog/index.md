---
uid: eQewVsCgikTmsnrgpUhx
title: 🐻 Better Admonitions for Bear Blog
slug: better-admonitions-for-bear-blog
alias: ""
published_date: "2025-12-23T07:23:00+00:00"
all_tags: "[\"bearblog\", \"blog\", \"blogging\", \"coding\", \"plugin\"]"
publish: "True"
make_discoverable: "True"
is_page: "False"
canonical_url: ""
meta_description: ""
meta_image: "https://bear-images.sfo2.cdn.digitaloceanspaces.com/fischr/md-admonitions.webp"
lang: en
class_name: ""
first_published_at: "2025-12-23T07:11:00+00:00"
---

I was looking around for some nice admonitions to add to my Bear Blog theme. I eventually found [some](https://thecommabandit.bearblog.dev/cohost-infoboxes/) and decided to use them. However, copy-pasting the complex div structure felt painful. It was impossible to add Markdown links to these boxes without resorting to raw HTML, which even more felt like tag-soup. To make my life at least a little bit easier, I added buttons to the Markdown toolbar I [released earlier](/a-markdown-toolbar-for-lazy-bear-blog-users/), to at least not need to copy-paste them anymore.

By accident, I later found out, [how GitHub handles Admonitions](https://github.com/orgs/community/discussions/16925) using simple Markdown. Unfortunately, this doesn't work in Bear Blog, but I very much liked the idea to have callout-boxes only by typing Markdown. So, I hacked a way around it.

I decided to repurpose the lower-level headings inside a blockquote. This keeps the content in pure Markdown while giving the browser enough "hooks" to style them as Info, Warning, or Caution boxes.

## How it works

To use this, just add the H4, H5, or H6 headline inside your blockquote, and you are done. Below you can see, what you need to type and how it is rendered, based on the CSS you find below.

```
> #### Important information
> Crucial information necessary for users to succeed.
```
> #### Important information
> Crucial information necessary for users to succeed.


```
> ##### Don't ignore this warning!
> Critical information demanding user attention due to potential risks.
```


> ##### Don't ignore this warning!
> Critical information demanding user attention due to potential risks.


```
> ###### THIS IS REALLY DANGEROUS!
> Negative potential consequences of an action.
```


> ###### THIS IS REALLY DANGEROUS!
> Negative potential consequences of an action.

## The CSS

Add the following CSS to your Bear Blog theme to transform those headings into beautiful, GitHub-style boxes.

```CSS
/* ==========================================================================
   GitHub Style Admonitions (Info, Warning and Caution Boxes)
   ========================================================================== */

blockquote:has(h4), blockquote:has(h5), blockquote:has(h6) {
    border: none !important;
    border-left: 3px solid !important;
    padding: 0 0 0 12px !important;
    margin: 3rem 0 !important;
    background-color: transparent !important;
    border-radius: 0 !important;
    text-align: left !important;
    font-family: var(--font-face) !important;
    font-size: 0.9em !important;
    line-height: 1.5 !important;
    max-width: var(--width);
}

blockquote:has(h4, h5, h6) p {
    margin: 0 !important;
    padding: 0 !important;
}

blockquote h4, blockquote h5, blockquote h6 {
    margin: 0 0 4px 0 !important;
    font-size: 1rem !important;
    font-family: var(--font-face) !important;
    text-transform: none !important;
    font-weight: 700 !important;
    display: flex;
    align-items: center;
}

blockquote h4::before, blockquote h5::before, blockquote h6::before {
    display: inline-block;
    width: 20px;
    height: 20px;
    margin-right: 8px;
    background-repeat: no-repeat;
    background-size: contain;
}

/* Info (H4) */
blockquote:has(h4) { border-color: #0969da !important; }
blockquote h4 { color: #0969da !important; }
blockquote h4::before {
    content: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='%230969da'%3E%3Cpath d='M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8Zm8-6.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13ZM6.5 7.75A.75.75 0 0 1 7.25 7h1a.75.75 0 0 1 .75.75v2.75h.25a.75.75 0 0 1 0 1.5h-2a.75.75 0 0 1 0-1.5h.25v-2h-.25a.75.75 0 0 1-.75-.75ZM8 6a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z'%3E%3C/path%3E%3C/svg%3E") / "Info: ";
}

/* Warning (H5) */
blockquote:has(h5) { border-color: #9a6700 !important; }
blockquote h5 { color: #9a6700 !important; }
blockquote h5::before {
    content: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='%239a6700'%3E%3Cpath d='M6.457 1.047c.659-1.234 2.427-1.234 3.086 0l6.082 11.378A1.75 1.75 0 0 1 14.082 15H1.918a1.75 1.75 0 0 1-1.543-2.575Zm1.763.707a.25.25 0 0 0-.44 0L1.698 13.132a.25.25 0 0 0 .22.368h12.164a.25.25 0 0 0 .22-.368Zm.53 3.996v2.5a.75.75 0 0 1-1.5 0v-2.5a.75.75 0 0 1 1.5 0ZM9 11a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z'%3E%3C/path%3E%3C/svg%3E") / "Warning: ";
}

/* Caution (H6) */
blockquote:has(h6) { border-color: #cf222e !important; }
blockquote h6 { color: #cf222e !important; }
blockquote h6::before {
    content: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16' fill='%23cf222e'%3E%3Cpath d='M4.47.22A.749.749 0 0 1 5 0h6c.199 0 .389.079.53.22l4.25 4.25c.141.14.22.331.22.53v6a.749.749 0 0 1-.22.53l-4.25 4.25A.749.749 0 0 1 11 16H5a.749.749 0 0 1-.53-.22L.22 11.53A.749.749 0 0 1 0 11V5c0-.199.079-.389.22-.53Zm.84 1.28L1.5 5.31v5.38l3.81 3.81h5.38l3.81-3.81V5.31L10.69 1.5ZM8 4a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 4Zm0 8a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z'%3E%3C/path%3E%3C/svg%3E") / "Caution: ";
}
```

## Why this approach makes sense

Yeap, I'm aware that headings have semantic meaning. However, there are several reasons why this is actually a superior solution for a blog:

- By using H4-H6, you stay entirely within the Markdown syntax. This allows you to use links, bold text, or even lists inside your boxes, without having to add messy HTML and ending up in tag-soup.

- This solution keeps your Markdown source code clean and readable. You don't have to worry about broken HTML tags or complex snippets in your editor. It’s about keeping the writing process as simple and clean as possible.

- This approach is a win for both accessibility and portability. Screen readers and RSS readers often ignore custom CSS and rely purely on HTML structure. By using headings, your admonitions become meaningful "landmarks." A user can jump directly to a warning in their screen reader, and an RSS subscriber will see a bold, clear headline instead of a flat block of text that lost its styling.