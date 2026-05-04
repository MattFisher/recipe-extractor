# Recipe Extractor

Paste any recipe URL and get back structured ingredients, instructions, and a clean copy — ready for Apple Notes, Obsidian, or wherever you keep things.

**Live:** https://recipe-extractor-i6ug.onrender.com

## What it does

1. Fetches the page with a browser User-Agent
2. **Strategy 1:** Looks for Schema.org Recipe data in `<script type="application/ld+json">` tags
3. **Strategy 2 (fallback):** Scrapes the DOM using class-name patterns for popular recipe plugins (WPRM, Tasty, Mediavine) and generic heading traversal
4. Returns JSON `{schema, markdown, strategy, title, url}` — also rendered in a clean web UI

The source URL is included in every output for provenance. See [`docs/schema.md`](docs/schema.md) for field reference and plugin notes.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py          # http://localhost:8000
```

The dev server hot-reloads on file changes. A **Test fixtures** bar appears below the URL input with saved sample pages (no network requests needed) — see [`tests/fixtures/`](tests/fixtures/).

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

## Deployment

The app is deployed on Render at **https://recipe-extractor-i6ug.onrender.com**.

- **Auto-deploy:** every push to `master` on [MattFisher/recipe-extractor](https://github.com/MattFisher/recipe-extractor) triggers a new deploy automatically.
- **Dashboard:** https://dashboard.render.com/web/srv-d7dictflk1mc73epa140
- **Plan:** Free tier (Oregon). Spins down after ~15 min of inactivity; first request after sleep takes ~30 s to wake.

### Re-deploy from scratch on a new Render account

1. Fork or push the repo to GitHub
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect the repo — Render detects `render.yaml` and pre-fills build/start commands
4. Click **Deploy**

`render.yaml` sets:

```yaml
buildCommand: pip install -r requirements.txt
startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
```
