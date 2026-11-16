# Računi i ključevi: popis koraka

Sve ovo je besplatno. Treba ti oko 45 minuta i mobitel za SMS potvrde.

> **Šifre i ključeve spremaj u [Bitwarden](https://bitwarden.com)** (besplatan upravitelj lozinki), a ne u .txt datoteku.
> Ključeve (API keys) upisuješ samo u `.env` na serveru, nikad u Git.

Kvačice odznačavaj kako ideš. Imena i opise kopiraš iz `branding/OPISI.md`.

## 1. Osnova

- [ ] **Bitwarden** račun (bitwarden.com), za sve šifre ispod
- [ ] **Novi Gmail** za kanal, npr. `bytecrewai@gmail.com` (potvrda SMS-om)
  - uključi dvostupanjsku provjeru (Google račun → Security → 2-Step Verification)

## 2. Kanali

- [ ] **YouTube kanal**: youtube.com prijavljen tim Gmailom → *Create a channel*
  - ime i korisničko ime iz `OPISI.md`, logo `logo.png`, banner `youtube-banner.png`, opis kanala
  - **youtube.com/verify**: potvrdi broj mobitela. Bez toga nema vlastitih thumbnailova.
- [ ] **TikTok** (registracija Gmailom): ime, bio, `logo.png`
- [ ] **Instagram** (registracija Gmailom): ime, bio, `logo.png`
  - Settings → *Account type and tools* → **Switch to professional account** → *Creator*
- [ ] **Facebook stranica** (treba je Instagram API): na Facebooku *Create Page* "Byte Crew"
  - u postavkama stranice → *Linked accounts* → poveži Instagram

## 3. Besplatni AI ključevi (upisuješ ih u `.env`)

- [ ] **Gemini**: aistudio.google.com/apikey → *Create API key* → `GEMINI_API_KEY`
- [ ] **Groq**: console.groq.com/keys → `GROQ_API_KEY`
- [ ] **OpenRouter**: openrouter.ai/keys → `OPENROUTER_API_KEY`
- [ ] **Pexels** (snimke): pexels.com/api → `PEXELS_API_KEY`
- [ ] **Claude** (tvoja pretplata): na svom računalu instaliraj Claude Code, pokreni
  `claude setup-token`, a dobiveni token upiši u `CLAUDE_CODE_OAUTH_TOKEN`.
  Sustav ga koristi najviše `CLAUDE_CODE_DAILY_LIMIT` puta dnevno (zadano 6), uglavnom za scenarije dugih videa.

## 4. Server i adresa

- [ ] **Oracle Cloud**: postupak je u `ORACLE.md`
- [ ] **DuckDNS**: duckdns.org → prijava Googleom → napravi poddomenu, npr. `bytecrew` → `bytecrew.duckdns.org`

## 5. Aplikacije za objavu (developer računi)

Za ovo ti treba adresa servera (korak 4).

- [ ] **Google Cloud** (YouTube): console.cloud.google.com
  1. novi projekt "Byte Crew" → *APIs & Services* → *Enable APIs* → **YouTube Data API v3**
  2. *OAuth consent screen* → External → dodaj svoj Gmail pod *Test users*
  3. *Credentials* → *Create credentials* → *OAuth client ID* → *Web application*
     → Redirect URI: `https://bytecrew.duckdns.org/auth/youtube/callback`
  4. → `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`
  5. kasnije: zatraži **audit** (obrazac *YouTube API Services – Audit and Quota Extension*). Do tada su videi privatni.
- [ ] **TikTok for Developers**: developers.tiktok.com → *Manage apps* → *Connect an app*
  1. dodaj **Login Kit** i **Content Posting API**
  2. Redirect URI: `https://bytecrew.duckdns.org/auth/tiktok/callback`
  3. → `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`
  4. pošalji aplikaciju na pregled (*Submit for review*) za izravnu objavu. Do tada `TIKTOK_MODE=inbox`.
- [ ] **Meta for Developers** (Instagram): developers.facebook.com → *Create app* → tip *Business*
  1. dodaj proizvod **Instagram** (Instagram API with Facebook Login)
  2. u *Graph API Explorer*: odaberi aplikaciju, dozvole `instagram_basic`, `instagram_content_publish`,
     `instagram_manage_comments`, `pages_show_list`, `pages_read_engagement` → *Generate Access Token*
  3. token pretvori u dugotrajni (*Access Token Debugger* → *Extend Access Token*), pa ga upotrijebi za
     `GET me/accounts`. Token stranice koji tamo dobiješ ne istječe.
  4. `GET {page-id}?fields=instagram_business_account` → to je `INSTAGRAM_USER_ID`
  5. token stranice → `INSTAGRAM_ACCESS_TOKEN`

## 6. Na kraju, na ploči

- [ ] YouTube kartica → **Poveži račun**
- [ ] TikTok kartica → **Poveži račun**
- [ ] Instagram kartica pokazuje broj objava (bez upozorenja) → povezan je
