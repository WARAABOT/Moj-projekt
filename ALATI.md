# Alati za Claude Code u ovom projektu

Postavke su u `.claude/settings.json`, pa ih dobije svaki Claude Code koji otvori ovaj projekt (računalo i oblak / mobitel).

| # | Alat | Izvor | Status |
|---|------|-------|--------|
| 1 | Ponytail | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | ✅ dodano (plugin) |
| 2 | OmniRoute | [diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute) | 💻 samo na računalu, upute dolje |
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

## 2. OmniRoute (radi samo na tvom računalu)
Službeni repozitorij: [diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute), MIT licenca, npm paket `omniroute`.
To nije plugin nego program (server) koji radi na tvom računalu, pa se ne može upisati u ovaj projekt.
U oblaku i na mobitelu ga Claude Code ne može koristiti.

### Instalacija (Windows / Mac / Linux, treba Node.js)
```bash
npm install -g omniroute
omniroute
```
Ako npm 11+ blokira skripte, koristi naredbu koju ti npm ispiše u upozorenju (`--allow-scripts=...`).

### Postavljanje
1. Otvori `http://localhost:20128` u pregledniku.
2. **Providers**: dodaj pružatelje (vlastiti API ključ ili prijava). Besplatni često traže registraciju.
3. **Endpoints**: kopiraj svoj OmniRoute API ključ.

### Pokretanje Claude Codea kroz OmniRoute
```bash
omniroute run claude --model auto
```
Ova naredba ne mijenja trajne postavke. Običan `claude` i dalje ide direktno na Anthropic, a `omniroute run claude` ide kroz OmniRoute.
Ako nešto ne radi, `omniroute run claude --dry-run` pokaže što bi se pokrenulo.

### Na što paziti
- Tvoj kod i upiti idu pružatelju kojeg OmniRoute izabere. Za tajni kod biraj samo pružatelje kojima vjeruješ.
- Kad prebaci na besplatni model, to više nije Claude, nego slabiji model, pa je i kvaliteta slabija.
- Pružatelji označeni `tos: avoid` krše svoja pravila korištenja i mogu ti blokirati račun. Ne uključuj ih ručno.
- Ne koristi ga za provlačenje svoje Claude Pro/Max pretplate kroz tuđe servise. To može kršiti Anthropicova pravila.
- Ne uključuj opcije "TLS stealth" i "MITM decrypt" ako ne znaš točno što rade.
- Instaliraj samo `omniroute` s npm-a ili iz gornjeg repozitorija, ne iz forkova.

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

## Besplatni LLM API-ji (za OmniRoute)
Poznata lista `cheahjs/free-llm-api-resources` trenutno nije dostupna na GitHubu (vraća 404).
Postoje samo neslužbene kopije, pa ih ne preporučujem. Ovo su službeni besplatni API-ji velikih tvrtki.
Ključ dobiješ na njihovoj stranici i upišeš ga u OmniRoute pod **Providers**.

| Pružatelj | Gdje dobiti ključ | Napomena |
|---|---|---|
| Google AI Studio (Gemini) | aistudio.google.com | Najizdašniji besplatni sloj. Na besplatnom sloju Google može koristiti podatke za učenje. |
| Groq | console.groq.com | Vrlo brz, otvoreni modeli (Llama, Qwen…) |
| OpenRouter | openrouter.ai | Modeli s oznakom `:free`, dnevni limit |
| GitHub Models | github.com/marketplace/models | Prijava GitHub računom, mali limiti |
| Mistral (La Plateforme) | console.mistral.ai | Besplatni "Experiment" plan |
| Cerebras | cloud.cerebras.ai | Vrlo brz, dnevni limit tokena |

- Limiti i uvjeti se često mijenjaju. Prije korištenja provjeri ih na stranici pružatelja.
- API ključeve nikad ne stavljaj u ovaj repozitorij. Upiši ih samo u OmniRoute dashboard na svom računalu.
- Besplatni modeli su slabiji od Claudea. Dobri su za jednostavne zadatke, ali ne za veće projekte.

## Što NE postoji: "neograničeno"
- Nijedan alat ne daje neograničen Claude. Limit ovisi o tvom planu (Pro / Max) ili o potrošnji API-ja.
- Alati iznad samo troše manje tokena po zadatku, pa s istim limitom napraviš više.
- "Neograničeno besplatno" (OmniRoute, claude-code-router) znači da posao radi neki drugi, slabiji model, a tvoj kod ide drugim tvrtkama.
- Ako ti stvarno treba više, uzmi veći plan (Max) ili API s plaćanjem po potrošnji.
