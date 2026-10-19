# hustle-research-brief

**SaaS pricing snapshot research brief** — a digital-download SKU pipeline (Hustle Tier 0 §4).

Collect public competitor pricing pages and/or RSS feeds into structured CSV rows, draft a Markdown narrative brief, **human-approve**, then **export** a zip/folder under `out/export/` ready for Gumroad free-tier upload. **No Gumroad API upload** — you upload the pack yourself.

## Workflow

```
Collect/draft → Human approve → Export pack → You upload to Gumroad
```

| Step | Command | Result |
|------|---------|--------|
| 1. Collect | `python src/cli.py --demo` (or `--live`) | `out/data.csv`, `out/brief.md` |
| 2. Approve | Review files, then `python src/cli.py approve --yes` | `out/.approval.json` |
| 3. Export | `python src/cli.py export` | `out/export/<sku>-YYYY-MM-DD/` + `.zip` |
| 4. Upload | Gumroad product UI (free tier) | Manual — tool does not call Gumroad |

## Requirements

- Python 3.11+
- Optional: `OPENAI_API_KEY` for an LLM-polished brief (otherwise a template narrative is used)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp config.example.yaml config.yaml   # optional; repo ships a demo config.yaml
```

## Run (dry-run)

Offline fixtures (default in `config.yaml`):

```bash
python src/cli.py --demo
# equivalent: python src/cli.py run --demo

python src/cli.py approve --yes
python src/cli.py export
ls out/export/
```

Live fetch from URLs in config:

```bash
python src/cli.py --live
python src/cli.py approve --yes
python src/cli.py export --format zip
```

### Outputs

| Path | Contents |
|------|----------|
| `out/data.csv` | Structured pricing / RSS rows |
| `out/brief.md` | Narrative research brief |
| `out/.approval.json` | Human approval + checksums (required for export) |
| `out/export/<sku>-YYYY-MM-DD/` | Folder pack: `brief.md`, `data.csv`, `README.txt` |
| `out/export/<sku>-YYYY-MM-DD.zip` | Same pack zipped for Gumroad file upload |

Export formats: `--format both` (default), `zip`, or `folder`.

Re-running collect clears a prior approval so stale packs cannot ship.

## Config

Edit `config.yaml` (see `config.example.yaml`):

- `sources[]` — `type: pricing_page` or `type: rss` with public URLs
- `demo: true` — skip network; use bundled fixture rows
- `sku` — title / niche / audience for the brief and export pack name
- `fetch` — timeout, user-agent, max body bytes
- `output.export_dir` — subdirectory under `out/` (default `export`)

## Env

| Variable | Effect |
|----------|--------|
| `OPENAI_API_KEY` | If set, draft brief via OpenAI; else template |
| `OPENAI_MODEL` | Model id (default `gpt-4o-mini`) |

## Compliance

- Prefer official public pricing pages and RSS only.
- Polite HTTP GETs only — no browser evasion or ToS-breaking scrapers.
- Extracted prices are heuristics; spot-check before selling.
- Thin / stale content risks marketplace rejection — refresh weekly and bump “last updated”.
- Human must approve before export; upload to Gumroad remains manual.

## License

MIT
