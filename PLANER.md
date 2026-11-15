# Daily channel planner (instructions for the scheduled Claude Code session)

Kratko na hrvatskom: ovo je dnevni posao koji Claude Code radi sam. Napiše scenarije unaprijed,
pogleda statistiku i prilagodi strategiju. GitHub Actions od tih scenarija napravi i uploada videe.

## Your job, every day

You run the five faceless YouTube channels in `channels/*.toml`. You write the scripts; the GitHub
Actions workflow (`.github/workflows/videos.yml`, 13:41 UTC) turns them into videos and uploads them.
Your goal is channels that grow and reach the YouTube Partner Program honestly: videos people
actually want to watch, never spam.

### 1. Get the latest state
```bash
git fetch origin main content || git fetch origin main
```
Read from `origin/main`: `channels/*.toml`, `history/*.json` (what was uploaded, `script` = queue
file used), `stats/*.json` (views, likes, subscribers), and `faceless/write.py` (`SCHEMA` and
`FORMATS`: the exact JSON shape and length rules for scripts).

Work on the `content` branch (`git switch content`, or if it does not exist yet:
`git switch --orphan content`). The user has authorized pushing to this branch. Never push to `main`.

### 2. Review (Sundays, or when stats/ changed a lot)
Per channel, look at which topics, hooks and titles got the most views per day online and the best
like/view ratio. Write what you learned and the plan for next week to `strategy/<channel>.md`
(keep it short, newest on top). Use it when choosing topics. If a channel is clearly failing after
4+ weeks, write a recommendation in `strategy/REPORT.md` for the user (in Croatian).

### 3. Keep the queue full
A queued script is `queue/<channel>/<short|long>/<YYYY-MM-DD>-<slug>.json` (on `content`, or the
seed files in `queue/` on main). It counts as used when its file name appears as `script` in
`history/<channel>.json`. Keep for every channel:
- at least **3 unused shorts** (one is uploaded per day), and
- **1 unused long** script (uploaded on the channel's `long_days`, 0 = Monday).

Each file must match `SCHEMA` exactly: `topic, title, description, tags, thumbnail_text, scenes[]`
with `narration` and `footage_query`. Validate every file with `python -c "import json;json.load(open(f))"`.

### 4. Writing rules
- Follow the channel `brief` and `strategy/<channel>.md`. Never repeat a topic from history or queue.
- Accurate and specific. Verify any fact you are not sure of with WebSearch. No invented quotes,
  numbers or events. Say "legend says"/"scientists think" where it is not settled.
- gta6: always WebSearch news from the last few days first; label official vs rumor; never invent
  release details. Write gta6 shorts at most 2 days ahead, because news gets stale.
- Shorts: hook in the first sentence, 110-140 words, 5-8 scenes, title under 60 chars.
  Long: 1300-1600 words, 30-40 scenes, real structure, one natural call to subscribe at the end.
- `footage_query`: 2-4 generic English words that a free stock site has (e.g. "stormy ocean night").
  No brand, game or person names.
- Vary hooks, structure and title styles; each video must stand on its own, not a template.

### 5. Finish
Commit only `queue/` and `strategy/` on `content`, push with `git push -u origin content`
(retry network errors). Then reply with a 3-5 line summary in Croatian: what you wrote, what
the stats say, and anything the user must do (e.g. a secret is missing, the workflow failed).
