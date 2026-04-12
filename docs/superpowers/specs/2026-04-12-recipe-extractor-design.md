# Recipe Extractor — Design Spec
_Date: 2026-04-12_

## Overview

A recipe extraction tool that accepts a URL and returns structured recipe data (Schema.org JSON) plus a clean Markdown rendering. Delivered as both a FastAPI web app (with a single-file frontend) and a standalone CLI — sharing a common extraction core.

---

## Architecture

```
extractor.py   ← all extraction logic; no web dependencies
main.py        ← FastAPI thin wrapper; serves static/ at /
cli.py         ← argparse CLI; prints markdown or saves JSON
static/
  index.html   ← single-file mobile-first frontend
requirements.txt
render.yaml
README.md
```

**Dependency rule:** `extractor.py` imports only `requests`, `beautifulsoup4`, `lxml`, and stdlib. Neither `main.py` nor `cli.py` concerns are allowed to leak into it.

---

## extractor.py

### Public API

```python
@dataclass
class RecipeResult:
    schema: dict          # normalised Schema.org Recipe object
    markdown: str         # human-readable rendering
    strategy: Literal["schema_org", "heuristic"]
    title: str

def extract_recipe(url: str) -> RecipeResult: ...
```

### Fetch

- `requests.get` with a realistic browser `User-Agent` header
- Raises `ValueError` on non-2xx responses

### Strategy 1 — ld+json

Parse every `<script type="application/ld+json">` tag.  
Find a node where `@type == "Recipe"`:
- Direct object: `{"@type": "Recipe", ...}`
- `@graph` wrapper: `{"@graph": [...]}` — search items
- List root: `[{...}, ...]` — search items

### Strategy 2 — Heuristic DOM scraping (fallback)

Class-name pattern matching for common recipe plugins:
- **WPRM**: `.wprm-recipe-*`
- **Tasty**: `.tasty-recipes-*`
- **Mediavine (mv)**: `.mv-recipe-*`

Generic fallback: heading traversal — find the first `<h1>`/`<h2>` that looks like a recipe title, then walk siblings for ingredient lists (`<ul>`) and instruction lists (`<ol>` or `<li>` sequences).

### normalize_recipe(raw: dict) → dict

Trims to a clean Schema.org Recipe shape. Fields kept:

```
name, author, description, image,
recipeYield, prepTime, cookTime, totalTime,
recipeIngredient, recipeInstructions,
recipeCategory, recipeCuisine, keywords
```

- Nested authors: `{"@type": "Person", "name": "..."}` → plain string
- Missing fields omitted (no `null` pollution)

### recipe_to_markdown(recipe: dict) → str

Renders the normalised recipe to Markdown:

- `# Title`
- Meta line: author · yield · prep · cook · total (omit missing)
- ISO 8601 duration parsing: `PT1H30M` → `"1 hr 30 min"`, `PT45M` → `"45 min"`
- `## Ingredients` — bulleted list
- `## Instructions` — numbered steps; `HowToSection` sections get `### Section Name` headings with numbered steps restarting per section

---

## main.py

- `POST /extract` — body `{"url": "..."}`, returns `RecipeResult` as JSON
- `GET /` — serves `static/index.html`
- Static files served from `static/` at root
- `PORT` env var (default `8000`) for Render.com compatibility
- Thin: calls `extract_recipe(url)`, catches `ValueError`, returns 422

---

## cli.py

```
python cli.py <url> [--json] [--out FILE]
```

- Default: prints Markdown to stdout
- `--json`: prints the full JSON result
- `--out FILE`: writes output to file (format inferred from extension: `.md` or `.json`)
- Exit code 1 on extraction failure, message to stderr

---

## static/index.html

Single self-contained file (no build step, no CDN dependencies beyond a system font stack).

**Design:** clean minimal, warm orange accent (`#f97316`).

**Interactions:**
- URL input + "Get Recipe" button; Enter key submits
- Loading spinner during fetch
- Recipe display: title, meta chips (author, yield, prep/cook/total), bulleted ingredients, numbered steps with coloured index badges
- Strategy badge: green `✓ Schema.org` or amber `⚙ Heuristic`
- "Copy for Notes" button — clipboard API with `execCommand` fallback for older Safari
- "Download JSON" button — slug-named `.json` file via `<a download>`
- Error display for failed extractions

**Mobile-first:**
- 16px minimum font size (prevents iOS auto-zoom on input focus)
- `env(safe-area-inset-*)` padding for notched iPhones
- Tested viewport: 375px (iPhone SE) upward

---

## requirements.txt

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
```

---

## render.yaml

```yaml
services:
  - type: web
    name: recipe-extractor
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: PORT
        value: 10000
    plan: free
```

---

## README.md

Sections: what it is, local run (venv + uvicorn), CLI usage, deploy to Render.
