# Recipe Extractor

Paste any recipe URL and get back structured ingredients, instructions, and a clean Markdown copy — ready for Apple Notes, Obsidian, or wherever you keep things.

## What it does

1. Fetches the page with a browser User-Agent
2. **Strategy 1:** Looks for Schema.org Recipe data in `<script type="application/ld+json">` tags
3. **Strategy 2 (fallback):** Scrapes the DOM using class-name patterns for popular recipe plugins (WPRM, Tasty, Mediavine) and generic heading traversal
4. Returns JSON `{schema, markdown, strategy, title, url}` — also shown in a clean web UI

The source URL is included in every output for provenance.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py          # starts on http://localhost:8000
```

## CLI usage

```bash
python cli.py https://example.com/chocolate-cake        # print markdown
python cli.py https://example.com/chocolate-cake --json # print JSON
python cli.py https://example.com/chocolate-cake --out cake.md
python cli.py https://example.com/chocolate-cake --out cake.json
```

## Run tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

## Deploy to Render

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your repo — Render will detect `render.yaml` and configure automatically
4. Click **Deploy**

The free tier spins down after inactivity; first request after sleep may take ~30 s.
