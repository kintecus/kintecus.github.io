# ostaps.net

Personal site and portfolio. Hugo static site with a brutalist monospace aesthetic, hosted on GitHub Pages.

Includes an AI chat widget that lets visitors ask questions about my background - powered by a Cloudflare Worker backend with LLM completions.

## Architecture

```plantuml
@startuml
title ostaps.net - architecture

skinparam componentStyle rectangle
skinparam backgroundColor transparent

package "GitHub Pages" {
  [Hugo Static Site] as hugo
  note right of hugo
    Custom theme
    IBM Plex Mono
    Brutalist aesthetic
  end note
}

package "Cloudflare" {
  [Worker API] as worker
  database "D1\n(conversations)" as d1
  [KV\n(rate limits)] as kv
}

cloud "LLM Provider" as llm {
  [Groq / Cerebras\n(free tier)] as model
}

[Visitor Browser] as browser

browser --> hugo : static pages
browser --> worker : chat messages\n(SSE stream)
worker --> model : completions API
worker --> d1 : log conversations
worker --> kv : check rate limits
hugo ..> browser : chat widget JS

@enduml
```

![ostaps.net architecture](https://www.plantuml.com/plantuml/svg/LL9DRzim3BthLn0vDOTao7M7eaiwz6Cj4C10T-Xsa6t65Yo97aKd6uRzzr5o0gGtYU-Hx_59TqaionIy4ISUWVG-fdL4WHLORdedsCZ4Q4mQN1mjsm0DXP4YHgdaZ_QmCcpiF5vHQjiC7TCKsnrvOX2sCIcaJSQC2jeEOV7Wv76gOQ-Nj82_1k3zSUe8Ah7Y6gXK_2VO1BqM5OmagkQwNe0EboB0Raf20QJ7WANmj7s5lSVVy4fnfcnv4kjT4h2ObAZJjOwnBJFDlojFEqzJU_1gzUpeE_6035_sJyNBgLmLQAtOsYPjkT_yY3SDnIDoKkCKqtAHgUqcztzxKvIjMlSkE4dBCcOuPjKcYy7YvKKDCnrTYrmwlG-p-0FJB_W4EsIisIQTT61448SypmdKei-ZtjzSSg9HRvbE2RcWzNmsvdo0rUgs10UV8SqXZpdy3_YyeJAQtWe4J2bJLBgglceNemrBSoPbVh6GwVejF9RzSrhNb7QZkASEFgHqpHYEHH2R0QwoCiNhUdrxsUJYwkJQJl_eSsNCdJwZVk3_)

## Stack

- **Site**: Hugo 0.134.2 (extended), custom layouts, plain CSS with custom properties
- **Hosting**: GitHub Pages, deployed via GitHub Actions on push to main
- **Chat backend**: Cloudflare Worker + D1 (SQLite) + KV (rate limiting)
- **LLM**: Groq/Cerebras free tier (swappable to Claude API)
- **Analytics**: Simple Analytics
- **Fonts**: IBM Plex Mono (homepage), Verdana (content pages)

## Development

```bash
hugo server -D       # local dev with drafts
hugo --gc --minify   # production build
```

## Chat widget

On desktop, the chat opens as a floating panel. On mobile, it navigates to a dedicated `/chat/` page to avoid iOS Safari keyboard issues.

The backend lives in a separate repo (ostap-chat Cloudflare Worker).
