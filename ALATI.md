# Alati za Claude Code u ovom projektu

Postavke su u `.claude/settings.json`, pa ih dobije svaki Claude Code koji otvori ovaj projekt (računalo i oblak / mobitel).

| # | Alat | Izvor | Status |
|---|------|-------|--------|
| 1 | Ponytail | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | ✅ dodano (plugin) |
| 2 | OmniRoute | [diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute) | ⚠️ nije dodano, vidi dolje |
| 3 | Graphify | [safishamsi/graphify](https://github.com/safishamsi/graphify), PyPI paket `graphifyy` | ✅ dodano (skill + hookovi) |
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

## 2. OmniRoute (namjerno nije dodan)
OmniRoute nije plugin. To je zaseban server (gateway) koji pokrećeš na svom računalu (`http://localhost:20128`) i kroz koji Claude Code šalje upite drugim AI tvrtkama.

- Tvoj kod i upiti odlaze tvrtkama s popisa. Mnoge besplatne mogu ih spremati ili koristiti za učenje.
- Treba mu stalno upaljen server i API ključevi, pa ne radi u oblaku ni na mobitelu.
- Na GitHubu postoji puno kopija (forkova). Službeni je `diegosouzapw/OmniRoute`.

Ako ga ipak želiš, instaliraj ga samo na svom računalu prema službenom README-u, i to samo za kod koji nije tajan.

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

## Što NE postoji: "neograničeno"
- Nijedan alat ne daje neograničen Claude. Limit ovisi o tvom planu (Pro / Max) ili o potrošnji API-ja.
- Alati iznad samo troše manje tokena po zadatku, pa s istim limitom napraviš više.
- "Neograničeno besplatno" (OmniRoute, claude-code-router) znači da posao radi neki drugi, slabiji model, a tvoj kod ide drugim tvrtkama.
- Ako ti stvarno treba više, uzmi veći plan (Max) ili API s plaćanjem po potrošnji.
