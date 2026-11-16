# AI Studio

AI tim koji sam radi kratke videe (glas + snimke + titlovi) i objavljuje ih na **YouTube Shorts**, **TikTok** i **Instagram Reels**. Ti sve pratiš na neonskoj ploči i samo odobravaš.

## Kako radi

| Agent | Što radi | Alat |
|---|---|---|
| **Scout** | Predlaže teme (uči iz tvojih najgledanijih videa) | Claude |
| **Writer** | Scenarij od 30–45 s, naslov, opis, hashtagovi | Claude |
| **Clipper** | Uspravne snimke za svaku scenu | Pexels (besplatno) |
| **Editor** | Glas, titlovi riječ po riječ, montaža 1080×1920 | ElevenLabs + ffmpeg |
| **Designer** | Naslovna slika (thumbnail) | Pillow |
| **Publisher** | Objava u tvojim terminima na sve platforme | YouTube, TikTok, Instagram API |
| **Analyst** | Pregledi, lajkovi, pratitelji | API-ji platformi |
| **Community** | Čita komentare i predlaže odgovore | Claude |

Na ploči u odjeljku **Treba tvoje odobrenje** odobravaš:
1. **teme** koje je Scout predložio,
2. **gotov video** prije objave (možeš ga pogledati),
3. **odgovore na komentare** (možeš ih prepraviti prije slanja).

Ako želiš da sve ide samo, u `.env` stavi `AUTO_APPROVE_TOPICS=true` i/ili `AUTO_APPROVE_PUBLISH=true`.

## Isprobaj odmah (demo)

Bez ijednog ključa sve se simulira, pa vidiš kako ploča radi. Video se stvarno izradi (s gradijentima umjesto snimki i bez glasa), a objave su lažne.

```bash
cd ai-studio
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Otvori http://localhost:8000. Treba ti instaliran `ffmpeg`.

## Postavljanje na server

1. **Server**: bilo koji VPS s Ubuntuom (Hetzner, DigitalOcean… od oko 5 € mjesečno, barem 2 GB RAM-a). Instaliraj Docker: `curl -fsSL https://get.docker.com | sh`
2. **Domena**: napravi A zapis, npr. `studio.mojadomena.com`, koji pokazuje na IP servera.
3. **Kod**: `git clone` ovaj repozitorij na server pa `cd Moj-projekt/ai-studio`.
4. **Postavke**: `cp .env.example .env` i popuni (vidi dolje). Obavezno postavi `DASHBOARD_PASSWORD`.
5. **Pokreni**: `docker compose up -d --build`
6. Otvori `https://studio.mojadomena.com`. HTTPS certifikat se napravi sam.

Ažuriranje: `git pull && docker compose up -d --build`. Podaci i videi ostaju u mapi `data/`.

## Ključevi

### Claude (obavezno)
[console.anthropic.com](https://console.anthropic.com) → API Keys → `ANTHROPIC_API_KEY`.
Kad je ključ upisan, demo se sam isključuje.

### ElevenLabs (glas)
[elevenlabs.io](https://elevenlabs.io) → profil → API key → `ELEVENLABS_API_KEY`.
Glas biraš u Voice Library i kopiraš njegov ID u `ELEVENLABS_VOICE_ID`.

### Pexels (snimke)
[pexels.com/api](https://www.pexels.com/api/) → besplatan ključ → `PEXELS_API_KEY`.

### YouTube
1. [console.cloud.google.com](https://console.cloud.google.com) → novi projekt → uključi **YouTube Data API v3**.
2. **OAuth consent screen**: External, dodaj svoj Gmail kao test usera.
3. **Credentials → Create OAuth client → Web application**, Redirect URI: `https://TVOJA-DOMENA/auth/youtube/callback`
4. Client ID i secret upiši u `.env`, restartaj, pa na ploči na YouTube kartici klikni **Poveži račun**.

Dok Google ne pregleda aplikaciju (audit), videi koje API objavi ostaju **privatni**. Zahtjev za audit šalješ preko obrasca *YouTube API Services – Audit and Quota Extension*. Besplatna kvota je oko 6 objava dnevno.

### TikTok
1. [developers.tiktok.com](https://developers.tiktok.com) → Manage apps → nova aplikacija.
2. Dodaj proizvode **Login Kit** i **Content Posting API**. Redirect URI: `https://TVOJA-DOMENA/auth/tiktok/callback`
3. Scope: `user.info.basic`, `user.info.stats`, `video.upload`, `video.publish`, `video.list`.
4. Client key i secret upiši u `.env`, pa na ploči klikni **Poveži račun**.

`TIKTOK_MODE=inbox` radi odmah: video stiže u TikTok aplikaciju kao obavijest, a ti ga objaviš jednim klikom.
Za potpuno automatsku objavu (`TIKTOK_MODE=direct`) TikTok mora odobriti tvoju aplikaciju. Dok to ne napravi, objave su vidljive samo tebi.
TikTokov API ne daje komentare, pa Community radi samo za YouTube i Instagram.

### Instagram Reels
1. Instagram račun prebaci u **Business** ili **Creator** i poveži ga s Facebook stranicom.
2. [developers.facebook.com](https://developers.facebook.com) → nova aplikacija → dodaj **Instagram Graph API**.
3. Dozvole: `instagram_basic`, `instagram_content_publish`, `instagram_manage_comments`, `pages_show_list`.
4. U Graph API Exploreru napravi **dugotrajni token** stranice i pronađi ID Instagram računa (`me/accounts?fields=instagram_business_account`).
5. Upiši `INSTAGRAM_USER_ID` i `INSTAGRAM_ACCESS_TOKEN`.

Instagram preuzima video s tvog servera, pa `PUBLIC_BASE_URL` mora biti javna HTTPS adresa.

## Troškovi (otprilike)

| Stavka | Cijena |
|---|---|
| Server | ~5 € mjesečno |
| Claude (tema + scenarij + odgovori) | ~0,03–0,08 $ po videu |
| ElevenLabs | Creator plan 22 $ mjesečno ≈ 150 videa |
| Pexels | besplatno |

3 videa dnevno ukupno izađu oko 35–45 € mjesečno.

## Struktura

```
app/
  main.py          web server, API za ploču, povezivanje računa
  orchestrator.py  pokreće agente u pozadini
  agents/crew.py   što svaki agent radi
  services/        glas, snimke, montaža, thumbnail, YouTube, TikTok, Instagram
web/               ploča (HTML, CSS, JS)
data/              baza i gotovi videi (ne ide u git)
```

## Dobro je znati

- Svi videi su označeni kao AI sadržaj (YouTube `containsSyntheticMedia`, TikTok `is_aigc`), jer platforme to traže.
- Ako neki korak pukne, video dobije status **Greška** s razlogom, a gumbom **Ponovi** ga vraćaš u red.
- Nemoj objavljivati isti tekst masovno na više kanala: platforme to vide kao spam.
