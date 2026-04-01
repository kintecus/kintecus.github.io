# ostaps.net

Personal site and portfolio. Hugo static site with a brutalist monospace aesthetic, hosted on GitHub Pages.

Includes an AI chat widget that lets visitors ask questions about my background - powered by a Cloudflare Worker backend with LLM completions.

## Architecture

```plantuml
@startuml
title ostaps.net - chat architecture

skinparam componentStyle rectangle
skinparam padding 4

package "ostaps.net (Hugo + GitHub Pages)" as frontend #E8F4FD {
  [chat-widget.html] as widget
  [chat.html (mobile)] as chatpage
  [Turnstile Widget] as tswidget #F3E8FD
}

package "Cloudflare Worker" as worker #E8F5E9 {
  [Validation + CORS] as handler
  [Turnstile Verify] as tsverify #F3E8FD
  [Rate Limiter] as ratelimit
  [FallbackProvider] as fallback
  [SSE Stream] as sse
}

cloud "LLM APIs" as llm #F3E8FD {
  [Cerebras (primary)] as cerebras
  [Groq (fallback)] as groq
}

database "D1 (logs)" as d1 #FFF8E1
database "KV (rate limits)" as kv #FFF8E1
cloud "Turnstile API" as tsapi #F3E8FD

widget --> handler : POST /chat
chatpage --> handler
tswidget ..> tsapi

handler --> tsverify
tsverify --> tsapi
tsverify --> ratelimit
ratelimit --> fallback
ratelimit --> kv
fallback --> cerebras
fallback ..> groq : on failure
sse --> handler : SSE
handler --> d1 : log

@enduml
```

![ostaps.net chat architecture](https://www.plantuml.com/plantuml/svg/NLFBRjim4BppAnREHK5X5qPJ8CqXI65RIL4NCQB0FGGvh2LQ9aoHwf9oO1JvzowfH-pUjBD3xkoCUESyacygBRpoMeBbkdOJ8psC8T-X1wHyfxpCVKDI2BTNfaR22d9RrTP8upD_v8F433IbbYUK6ej2cHAkXAWntsCfONGo87beIWkVu5xvXsO3A-wxon6WWorPuwKfu69ndLwbS_Wh05w2dF6RAahf9pjVwTT0RUk-7N58AhjHMbv6Ge1hlZfGdXiopdCBViTZaU1TUmTSf5zut5oydyYTQTiKMut4Hopj9KLzR_4pglkw-DQgMwDM1Nfb3QyqUtpAukKxD8MMT3vyBKbjZztmGoo6uKnyGYzXgIfsdIA96D2X3jqKjTwml1NPWoewnhO30o7B5f1vabZ5bdCoR9I7HM2qNFw2xwiVBgwXTTNFRNUOIP8RuavIawgGZfs57HmezsJ_GDBFQ_ibOs46huyRT6pRV0g9jcKNPp7bCMbwlPYUK7wk8GcBGToiO-uF0xCJ_E4Qonwrbc6j1hz45zvuVDkR3JUmUioUuNE8NlJvdpB4aFbaSjjUA4H_El3wMCIGJui6uXdq4Stm5V4Xa7DuVn1z9zQ3imCQ10K_UGd-axQeT7Xt7E9_6tBAPuhPunjWouMuuuV33_eV)

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
