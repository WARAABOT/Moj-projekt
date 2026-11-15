# Faceless YouTube kanali (automatski)

Svaki dan GitHub sam pokrene `faceless/main.py` i za svaki kanal:

1. **Claude** napiše scenarij, naslov, opis, tagove i tekst za thumbnail. Pazi da se teme ne ponavljaju (`history/`). Kanal o GTA 6 prvo pretraži internet za najnovije vijesti.
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

### 2. API ključevi
- **Claude:** platform.claude.com → API Keys. Uplati npr. 10–20 $.
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
| `ANTHROPIC_API_KEY` | Claude ključ |
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
- **Cijena:** Claude Opus 5.5 košta oko 15 $ mjesečno za ovaj raspored (~0,06 $ po Shortu, ~0,13 $ po dugom videu, plus pretraga za GTA). Ako želiš ispod 5 $, u `faceless/write.py` promijeni `MODEL` u `claude-haiku-5-5`. Bit će jeftinije, ali scenariji su slabiji. Sve ostalo je besplatno.
