# AI Studio · Byte Crew

AI tim koji sam radi videe i objavljuje ih:
- **kratke** (30–45 s, uspravne) 3 puta dnevno na **YouTube Shorts**, **TikTok** i **Instagram Reels**
- **duge** (8–12 min, vodoravne, s poglavljima) 2–3 puta tjedno na **YouTube**

Ti sve pratiš na neonskoj ploči i samo odobravaš. **Sve radi besplatno**: jedini trošak je tvoja Claude pretplata koju ionako imaš.

| Dokument | Što je u njemu |
|---|---|
| [`RACUNI.md`](RACUNI.md) | Popis računa i ključeva koje otvaraš, korak po korak |
| [`ORACLE.md`](ORACLE.md) | Postavljanje besplatnog servera |
| [`branding/OPISI.md`](branding/OPISI.md) | Ime kanala, opisi, bio, logo i banneri |

## Kako radi

| Agent | Što radi | Alat (cijena) |
|---|---|---|
| **Scout** | Predlaže teme, uči iz najgledanijih videa | AI mozak (0 €) |
| **Writer** | Scenarij, naslov, opis, hashtagovi, poglavlja | AI mozak (0 €) |
| **Clipper** | Snimke za svaku scenu | Pexels (0 €) |
| **Editor** | Glas, titlovi riječ po riječ, montaža | Kokoro + ffmpeg, na serveru (0 €) |
| **Designer** | Thumbnail | Pillow (0 €) |
| **Publisher** | Objava u tvojim terminima | API-ji platformi (0 €) |
| **Analyst** | Pregledi, lajkovi, pratitelji | API-ji platformi (0 €) |
| **Community** | Predlaže odgovore na komentare | AI mozak (0 €) |

**AI mozak** redom pita besplatne modele: Gemini → Groq → OpenRouter. Tvoju Claude pretplatu koristi samo:
- za scenarije dugih videa, gdje je kvaliteta najvažnija (2–3 puta tjedno),
- kad svi besplatni zakažu,
- i najviše `CLAUDE_CODE_DAILY_LIMIT` puta dnevno (zadano 6), pa ti ostane gotovo sav limit za tebe.

Svaki poziv vidiš u dnevniku na ploči (npr. "gemini odgovorio za 4 s").

Na ploči u **Treba tvoje odobrenje** odobravaš teme, gotove videe (možeš ih pogledati) i odgovore na komentare.
Ako želiš da sve ide samo, u **⚙ Kanali** uključi *odobri teme* i *objavi gotove videe* za taj kanal.

## Više kanala (profila)

Jedan dashboard vodi sve kanale. Gore lijevo biraš **Svi kanali** ili jedan kanal, a sve na ploči se filtrira po tom izboru.

Novi kanal dodaješ tipkom **⚙ Kanali → + Novi kanal**:
1. upišeš ime, temu (npr. "easy healthy recipes"), boju, glas i sate objave, pa klikneš **Spremi**,
2. klikneš **Napravi logo i banner** i preuzmeš slike za profile,
3. otvoriš račune za taj kanal (`RACUNI.md`, dio *Za svaki novi kanal*),
4. u istom prozoru klikneš **Poveži** za YouTube i TikTok, a za Instagram upišeš ID i token.

Svaki kanal ima svoju temu, jezik, glas, boju, termine, dane za duge videe i svoje račune.
Isti tim agenata radi za sve kanale, a u dnevniku i proizvodnji vidiš oznaku kanala.
Kanal možeš pauzirati (makni kvačicu *kanal je aktivan*): tada ne radi nove videe.

## Troškovi

| Stavka | Cijena |
|---|---|
| Server (Oracle Always Free) | 0 € |
| Adresa (DuckDNS) | 0 € |
| AI mozak (Gemini, Groq, OpenRouter) | 0 € |
| Glas (Kokoro) i snimke (Pexels) | 0 € |
| Claude pretplata (već je imaš) | 23 € mjesečno |

## Isprobaj na svom računalu (demo)

Bez ijednog ključa sve se simulira. Video se stvarno izradi, ali s gradijentima umjesto snimki i bez glasa, a objave su lažne.

```bash
cd ai-studio
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Otvori http://localhost:8000. Treba ti instaliran `ffmpeg`.

## Ograničenja platformi

- **YouTube:** dok Google ne napravi audit tvoje aplikacije, videi objavljeni preko API-ja ostaju **privatni**. Zahtjev šalješ jednom (vidi `RACUNI.md`). Za vlastiti thumbnail kanal mora biti potvrđen na youtube.com/verify.
- **TikTok:** dok TikTok ne odobri aplikaciju, `TIKTOK_MODE=inbox` šalje video u TikTok aplikaciju, a ti ga objaviš jednim klikom. TikTok ne daje komentare kroz API.
- **Instagram:** preuzima video s tvog servera, pa server mora imati javnu HTTPS adresu.
- **Besplatni AI modeli** imaju dnevne limite. Zato ih ima nekoliko, a sustav sam prelazi na sljedeći.
- Svi videi su označeni kao AI sadržaj (YouTube `containsSyntheticMedia`, TikTok `is_aigc`), jer platforme to traže.

## Struktura

```
app/
  main.py          web server, API za ploču, povezivanje računa
  orchestrator.py  pokreće agente u pozadini
  llm.py           AI mozak (besplatni modeli + tvoja Claude pretplata)
  agents/crew.py   što svaki agent radi (kratki i dugi videi)
  services/        glas, snimke, montaža, thumbnail, YouTube, TikTok, Instagram
web/               ploča (HTML, CSS, JS)
branding/          logo, banneri, opisi
scripts/           make_branding.py: ponovno napravi logo i bannere
data/              baza, videi i Kokoro model (ne ide u git)
```

Ako neki korak pukne, video dobije status **Greška** s razlogom, a gumbom **Ponovi** ga vraćaš u red.
