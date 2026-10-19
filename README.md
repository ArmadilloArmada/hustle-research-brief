# hustle-research-brief

**SaaS pricing snapshot research brief** — a digital-download SKU pipeline (Hustle Tier 0 §4).

Collect public competitor pricing pages and/or RSS feeds into structured CSV rows, then draft a Markdown narrative brief for human QA before you list it on Gumroad (or similar). **No Gumroad upload in v1.**

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

## Run

Offline dry-run (demo fixtures — default in `config.yaml`):

```bash
python src/cli.py --demo
```

Live fetch from URLs in config:

```bash
python src/cli.py --live
```

Outputs:

| Path | Contents |
|------|----------|
| `out/data.csv` | Structured pricing / RSS rows |
| `out/brief.md` | Narrative research brief |

## Config

Edit `config.yaml` (see `config.example.yaml`):

- `sources[]` — `type: pricing_page` or `type: rss` with public URLs
- `demo: true` — skip network; use bundled fixture rows
- `sku` — title / niche / audience for the brief
- `fetch` — timeout, user-agent, max body bytes

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

## License

MIT
