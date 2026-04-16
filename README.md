# ostaps.net

Personal site and portfolio. Hugo static site with a brutalist monospace aesthetic, hosted on GitHub Pages.

Includes an AI chat widget that lets visitors ask questions about my background - powered by a Cloudflare Worker backend with LLM completions.

## Architecture

```mermaid
%%{init: {'theme':'base','flowchart':{'curve':'basis','nodeSpacing':70,'rankSpacing':100}}}%%
flowchart TD
    accTitle: ostaps.net chat architecture
    accDescr: Hugo frontend on GitHub Pages posts chat requests to a Cloudflare Worker that validates via Turnstile, rate-limits via KV, streams completions from Cerebras with a Groq fallback, and logs to D1.

    subgraph Frontend["ostaps.net (Hugo + GitHub Pages)"]
        widget[chat-widget.html]
        chatpage["chat.html (mobile)"]
        tswidget[Turnstile Widget]
    end

    subgraph Worker["Cloudflare Worker"]
        handler[Validation + CORS]
        tsverify[Turnstile Verify]
        ratelimit[Rate Limiter]
        fallback{{FallbackProvider}}
        sse[SSE Stream]
    end

    subgraph LLM["LLM APIs"]
        cerebras[Cerebras primary]
        groq[Groq fallback]
    end

    d1[(D1 logs)]
    kv[(KV rate limits)]
    tsapi[Turnstile API]

    widget -->|POST /chat| handler
    chatpage --> handler
    tswidget -.-> tsapi

    handler --> tsverify
    tsverify --> tsapi
    tsverify --> ratelimit
    ratelimit --> fallback
    ratelimit --> kv
    fallback --> cerebras
    fallback -.->|on failure| groq
    sse --> handler
    handler --> d1

    classDef storage fill:#ecfdf5,stroke:#16a34a,color:#064e3b;
    classDef external fill:#fef3c7,stroke:#d97706,color:#78350f;
    class d1,kv storage;
    class tsapi,cerebras,groq external;
```

## Stack

- **Site**: Hugo 0.134.2 (extended), custom layouts, plain CSS with custom properties
- **Hosting**: GitHub Pages, deployed via GitHub Actions on push to main
- **Chat backend**: Cloudflare Worker + D1 (SQLite) + KV (rate limiting) + Turnstile (bot protection)
- **LLM**: Cerebras (primary) + Groq (fallback), both free tier, swappable via LLMProvider interface
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
