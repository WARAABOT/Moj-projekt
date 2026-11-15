# Faceless YouTube kanali (automatski)

> **Trenutno radi samo 1 kanal: Curious Universe** (`channels/science.toml`): 2 Shorta dnevno i dugi video srijedom i subotom.
> Ostali kanali čekaju u `channels/later/`. Kanal uključiš tako da njegovu datoteku vratiš u `channels/`.
> Za početak u koraku 3 napravi token samo za ovaj kanal, a u GitHub upiši samo `YT_TOKEN_SCIENCE`.

Sve je besplatno. Nema plaćenog API-ja.

**Svako jutro (10:17 UTC)** zakazana Claude Code sesija (tvoja pretplata) prati `PLANER.md`: pogleda statistiku (`stats/`), napiše scenarije za sljedeće dane i spremi ih na granu `content`. Za GTA 6 prvo pretraži najnovije vijesti. Nedjeljom napravi tjedni pregled i strategiju (`strategy/` na grani `content`).

**Svaki dan (13:41 UTC)** GitHub Actions za svaki kanal:

1. Uzme sljedeći neiskorišteni scenarij.
2. **Edge TTS** (besplatno) pročita tekst glasom.
3. **Pexels** (besplatno) da stock snimke za svaku scenu.
4. **ffmpeg** složi video s titlovima. Dugi video dobije i thumbnail.
5. Video se **uploada na YouTube**, a kopija ostane 7 dana u GitHubu (Actions → run → *videos*).

| Kanal | Datoteka | Short | Dugi video |
|---|---|---|---|
| Forgotten Files (povijest, misterije) | `channels/history.toml` | svaki dan | utorak |
| Money Explained Simply (financije) | `channels/money.toml` | svaki dan | srijeda |
| Curious Universe (znanost) | `channels/science.toml` | svaki dan | četvrtak |
| Untold Lives (životne priče) | `channels/stories.toml` | svaki dan | petak |
| Vice City Daily (GTA 6 vijesti) | `channels/gta6.toml` | svaki dan | subota |

Ime, glas, stil i dane mijenjaš u `.toml` datoteci. Novi kanal dodaš tako da kopiraš jednu `.toml` datoteku.

## Što ti moraš napraviti (jednom)

### 1. Napravi kanale
Na YouTubeu napravi 5 kanala. Najlakše je jedan Google račun s više kanala ("Brand account"): YouTube → Settings → *Add or manage your channels* → *Create a channel*.
Svaki kanal potvrdi brojem mobitela (youtube.com/verify). Bez toga nema thumbnaila ni videa dužih od 15 minuta.

### 2. Besplatni ključevi
- **Pexels:** pexels.com/api, besplatno.
- **YouTube:** console.cloud.google.com → novi projekt → *APIs & Services* → uključi **YouTube Data API v3** → *OAuth consent screen*: tip *External*, sebe dodaj kao *Test user*, pa *Publish app* (inače token istekne za 7 dana) → *Credentials* → *Create OAuth client ID* → *Desktop app* → preuzmi JSON kao `client_secret.json`.

### 3. Token za svaki kanal (na svom računalu)
```bash
pip install google-auth-oauthlib
python faceless/get_token.py client_secret.json
```
Otvori se preglednik. Izaberi **kanal** (ne svoj osobni račun) i klikni *Allow*. Ako piše "Google hasn't verified this app", klikni *Advanced → Go to ...* (aplikacija je tvoja). Ponovi za svih 5 kanala.

### 4. Upiši tajne u GitHub
Repo → *Settings → Secrets and variables → Actions → New repository secret*:

| Ime | Vrijednost |
|---|---|
| `PEXELS_API_KEY` | Pexels ključ |
| `YT_CLIENT_ID`, `YT_CLIENT_SECRET` | iz `client_secret.json` |
| `YT_TOKEN_HISTORY`, `YT_TOKEN_MONEY`, `YT_TOKEN_SCIENCE`, `YT_TOKEN_STORIES`, `YT_TOKEN_GTA6` | tokeni iz koraka 3 |

Kanal bez tokena se i dalje napravi, ali se ne uploada. Video možeš preuzeti iz GitHuba.

### 5. Prvi test
*Actions → Make and upload videos → Run workflow*: kanal `science`, format `short`, makni kvačicu *Upload*. Za ~5 minuta preuzmi video i pogledaj ga.

## Važno

- **Videi idu kao "Private"** dok Google ne odobri tvoj API projekt. Nove aplikacije YouTube sam zaključa na private. Zatraži audit: support.google.com/youtube/contact/yt_api_form. Do tada video u YouTube Studiju ručno prebaciš na Public (1 klik). Kad audit prođe, u GitHubu dodaj *Variable* `YT_PRIVACY` = `public`.
- **Limit:** 10.000 API jedinica dnevno, a 1 upload troši ~1.600. To je oko 6 uploada dnevno: 5 Shortsa i 1 dugi video, kako je i namješteno. Za više uploada treba drugi Google Cloud projekt.
- **Zarada:** YouTube ne monetizira "masovni, ponavljajući" sadržaj. Zato svaki kanal ima drugi glas, stil i format, a Claude mora pisati točne i korisne priče. Svaki tjedan pogledaj par videa i komentare. Kad nešto ne valja, promijeni `brief` u `.toml` datoteci.
- **GTA 6:** to je neslužbeni fan kanal. Ne ubacuj snimke iz trailera ni igre, Rockstar ih skida (Content ID). Sustav zato koristi samo Pexels snimke.
- **Cijena: 0 €.** Scenarije pišem ja kroz tvoju Claude Code pretplatu (troši dio njenog limita). Glas (Edge TTS), snimke (Pexels), YouTube API i GitHub Actions su besplatni. GitHub privatnim repoima daje 2.000 minuta mjesečno, a ovo troši otprilike 500–900. Plaćeni Claude API (`ANTHROPIC_API_KEY`) nije potreban. Koristi se samo ako ga dodaš, i to kad u redu nema scenarija.
