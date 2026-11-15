# Alati za Claude Code u ovom projektu

Postavke su u `.claude/settings.json`, pa ih dobije svaki Claude Code koji otvori ovaj projekt (računalo i oblak / mobitel).

| # | Alat | Izvor | Status |
|---|------|-------|--------|
| 1 | Ponytail | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | ✅ dodano (plugin) |
| 2 | Besplatni LLM API-ji | vidi dolje | 💻 na računalu, preko OpenRoutera |
| 3 | Graphify | [safishamsi/graphify](https://github.com/safishamsi/graphify), PyPI paket `graphifyy` | ✅ dodano (skill + hookovi) |
| 5 | ccusage | [ccusage/ccusage](https://github.com/ccusage/ccusage) | ✅ dodano (statusna traka) |
| 4 | Agent Skills | [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) | ✅ dodano (plugin) |

## 1. Ponytail
Tjera agenta da piše što manje koda (YAGNI, standardna biblioteka prije svega).
Pri prvom otvaranju projekta Claude Code pita smiješ li vjerovati projektu i instalirati plugin, pa odgovori s "da".
Ručno: `/plugin marketplace add DietrichGebert/ponytail` pa `/plugin install ponytail@ponytail`.
Hookovi samo pokreću lokalne Node skripte. Webhook za slanje statistike je isključen dok ga sam ne upišeš.

## 3. Graphify
Pretvara kod u graf znanja (`graphify-out/`) da agent ne čita iste datoteke opet i opet.
Skill je u `.claude/skills/graphify/`, pravila su u `.claude/CLAUDE.md`.
Na svakom računalu jednom instaliraj CLI (treba Python 3.10+):

```bash
uv tool install graphifyy     # ili: pipx install graphifyy
```

Paket se zove `graphifyy` (s dva y). Pazi da ne instaliraš nešto sličnog imena.
Graf napraviš u Claude Codeu naredbom `/graphify .`.
Ako `graphify` nije instaliran, hookovi se tiho preskoče i ništa se ne kvari.

## 4. Agent Skills (Addy Osmani)
Oko 24 do 25 skillova za planiranje, kodiranje, testiranje, review i objavu.
Ručno: `/plugin marketplace add addyosmani/agent-skills` pa `/plugin install agent-skills@addy-agent-skills`.

---

# Dodatni alati (druga runda)

## Službeni plugini (marketplace `claude-plugins-official`, Anthropic)
Upisani su u `.claude/settings.json` i automatski se nude pri otvaranju projekta.

| Plugin | Čemu služi |
|---|---|
| `superpowers` | Najpopularniji workflow: brainstorming, plan, TDD, rad s pod-agentima |
| `context7` | Svježa dokumentacija biblioteka, pa manje grešaka i manje pogađanja |
| `feature-dev` | Vođeni razvoj nove funkcije s agentima za istraživanje i arhitekturu |
| `security-guidance` | Upozorenja na sigurnosne propuste dok Claude piše kod |
| `frontend-design` | Ljepši i kvalitetniji web dizajn |

## Tvoji "zaposlenici" (pod-agenti u `.claude/agents/`)
Pozivaš ih npr. s "neka istrazivac pronađe gdje se radi login".

| Agent | Model | Posao |
|---|---|---|
| `istrazivac` | haiku (najjeftiniji) | Pretražuje kod i vraća samo sažetak, pa štedi tokene glavnog agenta |
| `planer` | sonnet | Pravi plan prije većeg posla |
| `tester` | sonnet | Piše i pokreće testove |
| `recenzent` | sonnet | Pregledava promjene prije commita |

## Samo za računalo (treba program instaliran lokalno)
- **RTK** ([rtk-ai/rtk](https://github.com/rtk-ai/rtk)): skraćuje izlaz terminalskih naredbi prije nego ga Claude pročita (proizvođač navodi 60–90 %).
  Instalacija: `brew install rtk` ili `cargo install --git https://github.com/rtk-ai/rtk`, pa `rtk init --global`.
  Pazi: postoji drugi program istog imena. Provjeri s `rtk gain`.
- **Caveman**: Claude odgovara puno kraće (~65 % manje izlaznih tokena). Nije uključen jer su objašnjenja onda jako šturа. Uključi ga samo ako ti ne trebaju.

## ccusage (praćenje potrošnje tokena)
Službeni repozitorij: [ccusage/ccusage](https://github.com/ccusage/ccusage), MIT, npm paket `ccusage`.
Čita lokalne zapise Claude Codea i pokazuje koliko si tokena i novca potrošio. Ništa ne šalje van (statusna traka radi offline).

- **Statusna traka**: upisana je u `.claude/settings.json`, pa na dnu Claude Codea vidiš potrošnju uživo. Treba Node.js (`npx`).
- Ručno u terminalu:
```bash
npx ccusage@latest daily     # po danima
npx ccusage@latest monthly   # po mjesecima
npx ccusage@latest blocks    # 5-satni prozori limita, korisno da vidiš koliko ti je ostalo
```

## Besplatni LLM API-ji
Poznata lista `cheahjs/free-llm-api-resources` trenutno nije dostupna na GitHubu (vraća 404), pa je ovdje popis službenih besplatnih API-ja.

| Pružatelj | Gdje dobiti ključ | Radi direktno s Claude Codeom? |
|---|---|---|
| **OpenRouter** (modeli `:free`) | openrouter.ai | ✅ Da (vidi dolje) |
| Google AI Studio (Gemini) | aistudio.google.com | ❌ Samo za tvoje programe |
| Groq | console.groq.com | ❌ Samo za tvoje programe |
| GitHub Models | github.com/marketplace/models | ❌ Samo za tvoje programe |
| Mistral | console.mistral.ai | ❌ Samo za tvoje programe |
| Cerebras | cloud.cerebras.ai | ❌ Samo za tvoje programe |

### Claude Code s besplatnim modelima preko OpenRoutera
1. Registriraj se na openrouter.ai i napravi API ključ.
2. Izaberi besplatni model na openrouter.ai/models (filter "Free", ime završava na `:free`).
3. U terminalu na računalu (Mac/Linux):
```bash
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_AUTH_TOKEN="tvoj-openrouter-kljuc"
export ANTHROPIC_API_KEY=""
export ANTHROPIC_MODEL="ime-modela:free"
claude
```
Na Windowsu (PowerShell) umjesto `export X="..."` piši `$env:X="..."`.
Postavke vrijede samo u tom prozoru terminala. U novom prozoru `claude` opet radi normalno s Anthropicom.

### Na što paziti
- To **nije Claude**, nego drugi, slabiji model. OpenRouter sam upozorava da Claude Code s njima ne radi uvijek ispravno. Alati i skillovi znaju zakazati.
- Besplatni modeli imaju dnevne limite.
- API ključ nikad ne stavljaj u repozitorij.
- Neki besplatni pružatelji (npr. Gemini besplatni sloj) mogu koristiti tvoje podatke za učenje.

## Što NE postoji: "neograničeno"
- Nijedan alat ne daje neograničen Claude. Limit ovisi o tvom planu (Pro / Max) ili o potrošnji API-ja.
- Alati iznad samo troše manje tokena po zadatku, pa s istim limitom napraviš više.
- "Neograničeno besplatno" (besplatni API-ji, routeri) znači da posao radi neki drugi, slabiji model, a tvoj kod ide drugim tvrtkama.
- Ako ti stvarno treba više, uzmi veći plan (Max) ili API s plaćanjem po potrošnji.
