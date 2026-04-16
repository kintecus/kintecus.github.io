# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and development

- Run local dev server: `hugo server -D` (includes drafts)
- Build for production: `hugo --gc --minify`
- Hugo version: 0.134.2 (extended)
- CI deploys to GitHub Pages on push to `main` (.github/workflows/hugo.yaml)

## Site structure

- Custom layouts (no third-party theme) in `layouts/`
- Content uses YAML front matter (`---` delimiters)
- Standalone pages (about, colophon) use `layout: "page"` routing to `layouts/_default/page.html`
- Blog posts organized by year: `content/posts/YYYY/`
- Reading list: individual markdown files in `content/reading/` with book metadata in front matter params
- Static assets (CSS, images, favicon) in `static/`
- Base URL: https://ostaps.net

## Styling

- Plain CSS with CSS custom properties in `:root` (no preprocessor)
- Homepage: IBM Plex Mono monospace font, brutalist aesthetic (home-styles.css)
- Other pages: Verdana, sans-serif (styles.css)
- Max content width: 800px (homepage: 960px)
- Split nav on all pages: Home left, other links right
- External dependencies loaded via CDN: Google Fonts (IBM Plex Mono), Font Awesome 6.4.0, Simple Analytics

## Git

- Pre-commit hooks via pre-commit framework: markdownlint with --fix, Mermaid syntax validation
- Git LFS enabled
