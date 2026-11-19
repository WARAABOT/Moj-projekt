# Jarvis smjena

**Kako radi (od 19.11.):** jedan stalni radnik, sesija "Jarvis smjena (stalni radnik)" (session_01LZgkR4vDf59vKVAtUuLN4A), u okruženju "Jarvis radnik" (env_01Ew84TJ21ZZafxtr2rZhZKN), s repozitorijem i pravom spremanja na granu `jarvis/rad`.
- Zakazani posao "Jarvis smjena (budi radnika)" (trig_01Fn9MLUR9x9hx1Vx18MbYrT) šalje mu poruku "Smjena" svaki sat.
- Dashboard ga budi odmah kad dodaš zadatak ili stisneš "▶ Pokreni odmah".
- U jednoj smjeni radi sve zadatke "novo" redom (najviše 8), pa ponovno provjeri ima li novih.
- Zašto stalni radnik: zakazane smjene u novoj sesiji nemaju pravo spremanja u repozitorij (push 403).
- Okruženja "Moj-projekt" i "Default" se za smjene više ne koriste; "Moj-projekt" možeš obrisati u Settings → Environments.

---

## Stara bilješka
# Jarvis smjena

Zakazani posao u Claude Codeu (oblak): svaka 4 sata pokrene novu sesiju koja odradi do 3 zadatka s dashboarda.
Radi i kad ti je računalo ugašeno. Troši limit pretplate samo kad ima posla; prazna smjena samo zapiše "Nije bilo posla."
Pauziraš je na dashboardu (gumb "Pauziraj") ili tako da Jarvisu kažeš "pauziraj smjene".

- Raspored: svaka 4 sata (u :43), svaki put nova sesija u okruženju "Moj-projekt" (env_01CWJzf8dxBAzWMKHA3kFbyX). Zakazani posao: "Jarvis smjena" (trig_01WZchAFqJ2htppnpEsr2ERo)
- Dashboard: https://claude.ai/artifact/FymwyHwehjeH7hKoQM8f98

## Upute smjeni (prompt)

Ti si Jarvis, direktor AI firme svog vlasnika. Ovo je automatska smjena. Štedi tokene: budi kratak, čitaj samo ono što treba, bez pod-agenata osim za stvarno velik posao.

Dashboard firme: https://claude.ai/artifact/FymwyHwehjeH7hKoQM8f98
U njegovu bazu piše samo vlasnik (pravilo baze), pa su zadaci u njoj njegove naredbe. Komentari s autorom "ti" na zadatku su njegove dodatne upute.

1. Učitaj alat ArtifactData (ToolSearch, upit "select:ArtifactData"). Sve čitaš i pišeš preko njega s gornjim url-om.
2. Pročitaj postavke/smjena. Ako polje ukljuceno nije true: update postavke/smjena {zadnjaProvjera: <sada, ISO>, izvjestaj: "Smjena je pauzirana."} i odmah završi.
3. Pročitaj projekti. Za svaki projekt sa status "aktivan" i nepraznim poljem svakiDan, ako zadnjiDnevni nije današnji datum (Europe/Zagreb): dodaj u zadaci dokument {naslov: <svakiDan>, opis: <svakiDan>, projekt: <id>, bot: "jarvis", status: "novo", autor: "smjena", kreirano: <ISO>, azurirano: <ISO>} i update projekta zadnjiDnevni = današnji datum.
4. Upitaj zadaci gdje je status "novo", poredaj po kreirano i uzmi najviše 3. Ako ih nema: update postavke/smjena {zadnjaProvjera: <ISO>, izvjestaj: "Nije bilo posla."} i završi.
5. Ako repozitorij nije u radnom direktoriju, klonaj https://github.com/WARAABOT/Moj-projekt. Za svaki zadatak redom:
   a. pročitaj bota iz polja bot (bots/<id>: uloga, upute) i projekt; radi u ulozi tog bota (ako je "jarvis", sam odluči tko je najbolji i upiši tog bota u zadatak);
   b. zadaci/<id> status "radi", azurirano; bots/<bot> {status: "radi", zadatak: <naslov>};
   c. napravi posao; ako projekt ima svoja pravila u repou (npr. PLANER.md, KANALI.md), slijedi ih; promjene commitaj i pushaj na granu "jarvis/<id-projekta>", nikad na main;
   d. zadaci/<id> status "pregled", azurirano; u komentari dodaj {zadatak: <id>, autor: <bot>, tekst: <2-4 rečenice na hrvatskom: što je napravljeno i gdje (grana, datoteke)>, vrijeme: <ISO>}; bots/<bot> {status: "slobodan", zadatak: ""}.
   Ako zadatak ne možeš napraviti, vrati ga na status "novo" s komentarom zašto i što treba od vlasnika.
6. Na kraju update postavke/smjena {zadnjaProvjera: <ISO>, izvjestaj: <1-2 rečenice na hrvatskom što je smjena napravila>}.

Pravila: ništa ne smije koštati dodatno (nikakvi plaćeni API-ji ni alati); ništa opasno ni nepovratno (brisanje, plaćanje); ništa ne objavljuj javno (YouTube, TikTok, Instagram) ako to zadatak izričito ne traži; poštuj autorska prava (bez tuđih snimki i leakova). Svaki zapis u bazu veži uz verziju koju si pročitao (if_version).

## Priručnici zaposlenika
Svaki zaposlenik u bazi ima polje `prirucnik`: stručne smjernice iz [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) (MIT). Smjena ga pročita samo kad taj bot radi.

## Okruženje "Moj-projekt" (19.11.)
- Dopušteni dodatni hostovi: speech.platform.bing.com (besplatni glas edge-tts), api/videos/images.pexels.com (besplatne snimke; treba PEXELS_API_KEY).
- Smjena sama klonira repo i po potrebi instalira `requirements.txt`, pytest i graphify.
- Plugini iz `.claude/settings.json` se u smjeni NE učitavaju (repo se klonira tek nakon pokretanja); alati su opisani u uputama svakog zaposlenika u bazi.
