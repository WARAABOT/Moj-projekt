# Jesu li alati besplatni? (iz ALATI.md; requirements.txt ne postoji u repou)

| Alat | Cijena | Skriveni trošak / rizik |
|---|---|---|
| Ponytail, Graphify (`graphifyy`), ccusage, Playwright, claude-code-setup, code-review, commit-commands, superpowers, context7, security-guidance, frontend-design | besplatni (open source, MIT i sl.) | Troše tokene Claude pretplate (pluginske upute se šalju u svakoj poruci). Graphify `update` je bez API troška. |
| Claude Code | uključen u pretplatu | Limit ovisi o planu; ništa ne smije tražiti ANTHROPIC_API_KEY (plaćanje po potrošnji). |
| OpenRouter `:free` | besplatno | Dnevni limiti; slabiji modeli; kod ide trećoj strani. |
| Gemini / Groq / GitHub Models / Mistral / Cerebras | besplatni slojevi | Limiti; Gemini besplatni sloj može koristiti podatke za učenje; moguća naplata ako se pređe na plaćeni sloj. |
| claude-mem | besplatan | Za sažimanje troši dodatne tokene; „Cloud Sync” isključiti. |
| Headroom, OmniRoute, RTK, Caveman | besplatni | Samo računalo; OmniRoute šalje kod drugim pružateljima; ne koristiti oba s Headroomom. |
| task-observer | besplatan | Troši tokene. |
| edge-tts (pip) | paket besplatan | Koristi Microsoftov online glas bez ključa; usluga nije službeno zajamčena i može se promijeniti. U ovoj smjeni nije radio iz oblaka (TLS greška proxyja). |
| Pillow | besplatan | — |

**Zaključak:** ništa u ALATI.md ne traži plaćanje. Jedini realni „trošak” su tokeni/limit pretplate i rizik da besplatni servisi promijene uvjete. Nisam provjeravao cijene za svaki alat na službenim stranicama, već samo prema opisu u ALATI.md.
