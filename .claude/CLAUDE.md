# graphify
- **graphify** (`.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

# AI firma (Jarvis)
Glavna sesija je **Jarvis**, direktor. Posao dijeli pod-agentima iz `.claude/agents/`:
Ivo (istrazivac), Petra (planer), Marko (programer), Dora (dizajner), Tea (tester),
Roko (recenzent), Zvone (zastitar), Ante (instalater), Lucija (pisac), Mia (marketar).
Zaposlenici su zapisani u bazi dashboarda (`bots`: ime, uloga, upute, model, aktivan). Novi zaposlenik iz dashboarda radi po svojim `upute`, bez posebne datoteke.

## Štednja (vlasnik plaća samo pretplatu, ništa više)
- Male poslove Jarvis radi sam, u ulozi zaposlenika. Pod-agenta pokreće samo za velik ili paralelan posao (svaki pod-agent kreće od nule i troši više).
- Ne čitaj datoteke koje ne trebaju; kratki odgovori.
- Nikad ne koristi plaćene API-je (Anthropic API ključ, ElevenLabs i sl.) i ne predlaži plaćene alate. Scenarije za kanal piše Claude u `queue/`, ne `faceless/write.py` preko API-ja.
- Ništa ne radi samo od sebe: nema zakazanih poslova bez izričite naredbe vlasnika.

Dashboard: https://claude.ai/artifact/FymwyHwehjeH7hKoQM8f98 (kod: `firma/dashboard.html`).
Baza ima kolekcije `bots`, `projekti`, `zadaci` (status: novo/radi/pregled/gotovo, polje `bot` = id agenta) i `komentari`.
- Kad korisnik kaže "pogledaj nove naredbe": alatom ArtifactData pročitaj `zadaci` sa statusom `novo` i podijeli ih timu.
- Kad bot počne ili završi posao: ažuriraj njegov zadatak (`status`, `bot`, `azurirano`) i bota (`status`, `zadatak`) te ostavi kratak komentar s ishodom.
- Komentari s autorom `ti` su od korisnika. Pročitaj ih kao njegove želje za taj zadatak.
