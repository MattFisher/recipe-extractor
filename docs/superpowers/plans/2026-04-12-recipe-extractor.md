# Recipe Extractor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a recipe extraction tool (FastAPI web app + CLI) that accepts a URL and returns structured Schema.org recipe data plus a clean Markdown rendering.

**Architecture:** A shared `extractor.py` module handles all fetch/parse/normalize/render logic with zero web-framework dependencies. `main.py` is a thin FastAPI wrapper. `cli.py` is a thin argparse wrapper. The frontend is a single self-contained `static/index.html`.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, requests, BeautifulSoup4, lxml, pytest

---

## File Map

| File | Role |
|---|---|
| `extractor.py` | Core: fetch, parse, normalize, render — no framework deps |
| `main.py` | FastAPI: POST /extract, serves static/ |
| `cli.py` | argparse CLI: stdout markdown or JSON, --out file |
| `static/index.html` | Single-file mobile-first frontend |
| `requirements.txt` | Python dependencies |
| `render.yaml` | Render.com deploy config |
| `README.md` | Usage docs |
| `tests/test_extractor.py` | Unit tests for extractor.py |

---

## Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `static/.gitkeep`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
pytest>=8.0.0
```

- [ ] **Step 2: Create directory structure**

```bash
mkdir -p static tests
touch tests/__init__.py
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 4: Commit**

```bash
git init
git add requirements.txt tests/__init__.py
git commit -m "chore: project scaffold"
```

---

## Task 2: Duration parser

**Files:**
- Create: `extractor.py` (partial — duration function only)
- Create: `tests/test_extractor.py` (partial)

- [ ] **Step 1: Write failing tests for parse_duration**

Create `tests/test_extractor.py`:

```python
import pytest
from extractor import parse_duration


def test_hours_and_minutes():
    assert parse_duration("PT1H30M") == "1 hr 30 min"


def test_minutes_only():
    assert parse_duration("PT45M") == "45 min"


def test_hours_only():
    assert parse_duration("PT2H") == "2 hr"


def test_empty_string():
    assert parse_duration("") == ""


def test_invalid_returns_original():
    assert parse_duration("not-iso") == "not-iso"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_extractor.py -v
```

Expected: `ModuleNotFoundError: No module named 'extractor'`

- [ ] **Step 3: Implement parse_duration in extractor.py**

Create `extractor.py`:

```python
import re
import json
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Literal


BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


def parse_duration(iso: str) -> str:
    """Convert ISO 8601 duration to human-readable string.
    PT1H30M -> '1 hr 30 min', PT45M -> '45 min'
    """
    if not iso:
        return ""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", iso)
    if not m or (not m.group(1) and not m.group(2)):
        return iso
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    parts = []
    if hours:
        parts.append(f"{hours} hr")
    if minutes:
        parts.append(f"{minutes} min")
    return " ".join(parts)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extractor.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add extractor.py tests/test_extractor.py
git commit -m "feat: duration ISO 8601 parser with tests"
```

---

## Task 3: normalize_recipe

**Files:**
- Modify: `extractor.py` (add normalize_recipe)
- Modify: `tests/test_extractor.py` (add tests)

- [ ] **Step 1: Write failing tests for normalize_recipe**

Append to `tests/test_extractor.py`:

```python
from extractor import normalize_recipe


def test_normalize_strips_unknown_fields():
    raw = {"name": "Cake", "@type": "Recipe", "unknownField": "x"}
    result = normalize_recipe(raw)
    assert "unknownField" not in result
    assert "@type" not in result
    assert result["name"] == "Cake"


def test_normalize_removes_null_values():
    raw = {"name": "Cake", "description": None, "recipeYield": ""}
    result = normalize_recipe(raw)
    assert "description" not in result
    assert "recipeYield" not in result


def test_normalize_author_dict_to_string():
    raw = {"name": "Cake", "author": {"@type": "Person", "name": "Alice"}}
    result = normalize_recipe(raw)
    assert result["author"] == "Alice"


def test_normalize_author_list():
    raw = {
        "name": "Cake",
        "author": [
            {"@type": "Person", "name": "Alice"},
            {"@type": "Person", "name": "Bob"},
        ],
    }
    result = normalize_recipe(raw)
    assert result["author"] == ["Alice", "Bob"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_extractor.py::test_normalize_strips_unknown_fields -v
```

Expected: `ImportError: cannot import name 'normalize_recipe'`

- [ ] **Step 3: Implement normalize_recipe in extractor.py**

Append to `extractor.py` (after `parse_duration`):

```python
_RECIPE_FIELDS = {
    "name", "author", "description", "image",
    "recipeYield", "prepTime", "cookTime", "totalTime",
    "recipeIngredient", "recipeInstructions",
    "recipeCategory", "recipeCuisine", "keywords",
}


def normalize_recipe(raw: dict) -> dict:
    """Trim to clean Schema.org Recipe shape, resolve nested authors."""
    out = {k: v for k, v in raw.items() if k in _RECIPE_FIELDS and v not in (None, "", [], {})}

    if "author" in out:
        author = out["author"]
        if isinstance(author, list):
            out["author"] = [
                a.get("name", str(a)) if isinstance(a, dict) else a
                for a in author
            ]
        elif isinstance(author, dict):
            out["author"] = author.get("name", "")

    return out
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extractor.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add extractor.py tests/test_extractor.py
git commit -m "feat: normalize_recipe strips and flattens schema fields"
```

---

## Task 4: recipe_to_markdown

**Files:**
- Modify: `extractor.py` (add recipe_to_markdown)
- Modify: `tests/test_extractor.py` (add tests)

- [ ] **Step 1: Write failing tests for recipe_to_markdown**

Append to `tests/test_extractor.py`:

```python
from extractor import recipe_to_markdown


def test_markdown_title():
    recipe = {"name": "Chocolate Cake"}
    md = recipe_to_markdown(recipe)
    assert md.startswith("# Chocolate Cake")


def test_markdown_meta_line():
    recipe = {
        "name": "Cake",
        "author": "Alice",
        "recipeYield": "8 servings",
        "prepTime": "PT15M",
        "cookTime": "PT45M",
        "totalTime": "PT1H",
    }
    md = recipe_to_markdown(recipe)
    assert "By Alice" in md
    assert "Yield: 8 servings" in md
    assert "Prep: 15 min" in md
    assert "Cook: 45 min" in md
    assert "Total: 1 hr" in md


def test_markdown_ingredients():
    recipe = {"name": "Cake", "recipeIngredient": ["2 eggs", "1 cup flour"]}
    md = recipe_to_markdown(recipe)
    assert "## Ingredients" in md
    assert "- 2 eggs" in md
    assert "- 1 cup flour" in md


def test_markdown_flat_instructions():
    recipe = {
        "name": "Cake",
        "recipeInstructions": [
            {"@type": "HowToStep", "text": "Mix ingredients"},
            {"@type": "HowToStep", "text": "Bake 45 min"},
        ],
    }
    md = recipe_to_markdown(recipe)
    assert "## Instructions" in md
    assert "1. Mix ingredients" in md
    assert "2. Bake 45 min" in md


def test_markdown_howto_sections():
    recipe = {
        "name": "Cake",
        "recipeInstructions": [
            {
                "@type": "HowToSection",
                "name": "Batter",
                "itemListElement": [
                    {"@type": "HowToStep", "text": "Mix dry ingredients"},
                    {"@type": "HowToStep", "text": "Add wet ingredients"},
                ],
            },
            {
                "@type": "HowToSection",
                "name": "Baking",
                "itemListElement": [
                    {"@type": "HowToStep", "text": "Bake at 350F"},
                ],
            },
        ],
    }
    md = recipe_to_markdown(recipe)
    assert "### Batter" in md
    assert "1. Mix dry ingredients" in md
    assert "2. Add wet ingredients" in md
    assert "### Baking" in md
    assert "1. Bake at 350F" in md
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_extractor.py::test_markdown_title -v
```

Expected: `ImportError: cannot import name 'recipe_to_markdown'`

- [ ] **Step 3: Implement recipe_to_markdown in extractor.py**

Append to `extractor.py`:

```python
def recipe_to_markdown(recipe: dict) -> str:
    """Render a normalised recipe dict to Markdown."""
    lines = [f"# {recipe.get('name', 'Recipe')}", ""]

    # Meta line
    meta = []
    author = recipe.get("author")
    if author:
        if isinstance(author, list):
            meta.append("By " + ", ".join(author))
        else:
            meta.append(f"By {author}")
    if recipe.get("recipeYield"):
        meta.append(f"Yield: {recipe['recipeYield']}")
    for key, label in [("prepTime", "Prep"), ("cookTime", "Cook"), ("totalTime", "Total")]:
        if recipe.get(key):
            meta.append(f"{label}: {parse_duration(recipe[key])}")
    if meta:
        lines.append(" · ".join(meta))
        lines.append("")

    # Ingredients
    if recipe.get("recipeIngredient"):
        lines += ["## Ingredients", ""]
        for ing in recipe["recipeIngredient"]:
            lines.append(f"- {ing}")
        lines.append("")

    # Instructions
    instructions = recipe.get("recipeInstructions", [])
    if instructions:
        lines += ["## Instructions", ""]
        first = instructions[0] if instructions else {}
        if isinstance(first, dict) and first.get("@type") == "HowToSection":
            for section in instructions:
                lines += [f"### {section.get('name', 'Section')}", ""]
                for i, step in enumerate(section.get("itemListElement", []), 1):
                    text = step.get("text", "") if isinstance(step, dict) else step
                    lines.append(f"{i}. {text}")
                lines.append("")
        else:
            for i, step in enumerate(instructions, 1):
                text = step.get("text", "") if isinstance(step, dict) else step
                lines.append(f"{i}. {text}")
            lines.append("")

    return "\n".join(lines).strip()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extractor.py -v
```

Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add extractor.py tests/test_extractor.py
git commit -m "feat: recipe_to_markdown with HowToSection support"
```

---

## Task 5: Strategy 1 — ld+json extraction

**Files:**
- Modify: `extractor.py` (add `_find_recipe_in_ldjson`, `extract_schema_org`)
- Modify: `tests/test_extractor.py` (add tests)

- [ ] **Step 1: Write failing tests for ld+json parsing**

Append to `tests/test_extractor.py`:

```python
from bs4 import BeautifulSoup
from extractor import extract_schema_org


def _soup(ldjson: str) -> BeautifulSoup:
    return BeautifulSoup(
        f'<html><head><script type="application/ld+json">{ldjson}</script></head></html>',
        "lxml",
    )


def test_extract_schema_org_direct():
    soup = _soup('{"@type": "Recipe", "name": "Cake"}')
    result = extract_schema_org(soup)
    assert result is not None
    assert result["name"] == "Cake"


def test_extract_schema_org_graph_wrapper():
    soup = _soup('{"@graph": [{"@type": "WebPage"}, {"@type": "Recipe", "name": "Pie"}]}')
    result = extract_schema_org(soup)
    assert result["name"] == "Pie"


def test_extract_schema_org_list_root():
    soup = _soup('[{"@type": "WebPage"}, {"@type": "Recipe", "name": "Soup"}]')
    result = extract_schema_org(soup)
    assert result["name"] == "Soup"


def test_extract_schema_org_not_found():
    soup = _soup('{"@type": "WebPage", "name": "Some Page"}')
    result = extract_schema_org(soup)
    assert result is None


def test_extract_schema_org_invalid_json():
    soup = BeautifulSoup(
        '<html><head><script type="application/ld+json">{bad json}</script></head></html>',
        "lxml",
    )
    result = extract_schema_org(soup)
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_extractor.py::test_extract_schema_org_direct -v
```

Expected: `ImportError: cannot import name 'extract_schema_org'`

- [ ] **Step 3: Implement ld+json extraction in extractor.py**

Append to `extractor.py`:

```python
def _find_recipe_in_ldjson(data) -> dict | None:
    """Recursively search parsed ld+json for a Recipe node."""
    if isinstance(data, list):
        for item in data:
            found = _find_recipe_in_ldjson(item)
            if found:
                return found
    elif isinstance(data, dict):
        if data.get("@type") == "Recipe":
            return data
        if "@graph" in data:
            for item in data["@graph"]:
                if isinstance(item, dict) and item.get("@type") == "Recipe":
                    return item
    return None


def extract_schema_org(soup: BeautifulSoup) -> dict | None:
    """Strategy 1: find Recipe in any ld+json script tag."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            recipe = _find_recipe_in_ldjson(data)
            if recipe:
                return recipe
        except (json.JSONDecodeError, AttributeError):
            continue
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extractor.py -v
```

Expected: 19 passed.

- [ ] **Step 5: Commit**

```bash
git add extractor.py tests/test_extractor.py
git commit -m "feat: Strategy 1 ld+json extraction with graph/list support"
```

---

## Task 6: Strategy 2 — heuristic DOM scraping

**Files:**
- Modify: `extractor.py` (add `extract_heuristic`)
- Modify: `tests/test_extractor.py` (add tests)

- [ ] **Step 1: Write failing tests for heuristic extraction**

Append to `tests/test_extractor.py`:

```python
from extractor import extract_heuristic


def test_heuristic_wprm_plugin():
    html = """
    <div class="wprm-recipe-container">
      <span class="wprm-recipe-name">Pancakes</span>
      <li class="wprm-recipe-ingredient">1 cup flour</li>
      <li class="wprm-recipe-ingredient">1 egg</li>
      <div class="wprm-recipe-instruction">Mix and cook.</div>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")
    result = extract_heuristic(soup)
    assert result["name"] == "Pancakes"
    assert "1 cup flour" in result["recipeIngredient"]
    assert result["recipeInstructions"][0]["text"] == "Mix and cook."


def test_heuristic_generic_headings():
    html = """
    <h1>Simple Pasta</h1>
    <h2>Ingredients</h2>
    <ul>
      <li>200g pasta</li>
      <li>2 cloves garlic</li>
    </ul>
    <h2>Instructions</h2>
    <ol>
      <li>Boil pasta.</li>
      <li>Fry garlic.</li>
    </ol>
    """
    soup = BeautifulSoup(html, "lxml")
    result = extract_heuristic(soup)
    assert result["name"] == "Simple Pasta"
    assert "200g pasta" in result["recipeIngredient"]
    assert result["recipeInstructions"][0]["text"] == "Boil pasta."
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_extractor.py::test_heuristic_wprm_plugin -v
```

Expected: `ImportError: cannot import name 'extract_heuristic'`

- [ ] **Step 3: Implement extract_heuristic in extractor.py**

Append to `extractor.py`:

```python
def extract_heuristic(soup: BeautifulSoup) -> dict:
    """Strategy 2: class-name pattern matching + heading traversal."""
    recipe: dict = {}

    # Known plugin prefixes
    for prefix in ("wprm-recipe", "tasty-recipes", "mv-recipe"):
        container = soup.find(class_=re.compile(rf"^{re.escape(prefix)}(?:-container)?$"))
        if not container:
            continue

        name_el = container.find(class_=re.compile(rf"{re.escape(prefix)}-name$"))
        if name_el:
            recipe["name"] = name_el.get_text(strip=True)

        ings = container.find_all(class_=re.compile(rf"{re.escape(prefix)}-ingredient$"))
        if ings:
            recipe["recipeIngredient"] = [el.get_text(strip=True) for el in ings]

        steps = container.find_all(class_=re.compile(rf"{re.escape(prefix)}-instruction$"))
        if steps:
            recipe["recipeInstructions"] = [
                {"@type": "HowToStep", "text": el.get_text(strip=True)} for el in steps
            ]

        if recipe:
            break

    # Generic fallback: h1/h2 title
    if not recipe.get("name"):
        heading = soup.find(["h1", "h2"])
        if heading:
            recipe["name"] = heading.get_text(strip=True)

    # Generic fallback: ingredient list near "ingredients" heading
    if not recipe.get("recipeIngredient"):
        for h in soup.find_all(["h2", "h3", "h4"]):
            if "ingredient" in h.get_text(strip=True).lower():
                ul = h.find_next_sibling("ul")
                if ul:
                    recipe["recipeIngredient"] = [
                        li.get_text(strip=True) for li in ul.find_all("li")
                    ]
                    break

    # Generic fallback: instruction list near directions/instructions/method heading
    if not recipe.get("recipeInstructions"):
        for h in soup.find_all(["h2", "h3", "h4"]):
            label = h.get_text(strip=True).lower()
            if any(w in label for w in ("instruction", "direction", "method", "step")):
                ol = h.find_next_sibling("ol")
                if ol:
                    recipe["recipeInstructions"] = [
                        {"@type": "HowToStep", "text": li.get_text(strip=True)}
                        for li in ol.find_all("li")
                    ]
                    break

    return recipe
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_extractor.py -v
```

Expected: 21 passed.

- [ ] **Step 5: Commit**

```bash
git add extractor.py tests/test_extractor.py
git commit -m "feat: Strategy 2 heuristic DOM scraping (wprm/tasty/mv + generic)"
```

---

## Task 7: extract_recipe orchestration + fetch

**Files:**
- Modify: `extractor.py` (add `fetch_html`, `RecipeResult`, `extract_recipe`)
- Modify: `tests/test_extractor.py` (add integration test with mock)

- [ ] **Step 1: Write failing tests for extract_recipe**

Append to `tests/test_extractor.py`:

```python
from unittest.mock import patch, MagicMock
from extractor import extract_recipe, RecipeResult

_LDJSON_HTML = """
<html>
<head>
  <script type="application/ld+json">
    {"@type": "Recipe", "name": "Mock Cake", "recipeIngredient": ["2 eggs"],
     "recipeInstructions": [{"@type": "HowToStep", "text": "Mix and bake."}]}
  </script>
</head>
<body></body>
</html>
"""

_HEURISTIC_HTML = """
<html><body>
  <h1>Mock Soup</h1>
  <h2>Ingredients</h2><ul><li>Water</li></ul>
  <h2>Instructions</h2><ol><li>Boil water.</li></ol>
</body></html>
"""


def _mock_response(html: str) -> MagicMock:
    resp = MagicMock()
    resp.text = html
    resp.raise_for_status = MagicMock()
    return resp


def test_extract_recipe_schema_org():
    with patch("extractor.requests.get", return_value=_mock_response(_LDJSON_HTML)):
        result = extract_recipe("http://example.com/recipe")
    assert isinstance(result, RecipeResult)
    assert result.title == "Mock Cake"
    assert result.strategy == "schema_org"
    assert "# Mock Cake" in result.markdown
    assert isinstance(result.schema, dict)


def test_extract_recipe_heuristic_fallback():
    with patch("extractor.requests.get", return_value=_mock_response(_HEURISTIC_HTML)):
        result = extract_recipe("http://example.com/recipe")
    assert result.title == "Mock Soup"
    assert result.strategy == "heuristic"


def test_extract_recipe_http_error():
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.HTTPError("404")
    with patch("extractor.requests.get", return_value=resp):
        with pytest.raises(requests.HTTPError):
            extract_recipe("http://example.com/404")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_extractor.py::test_extract_recipe_schema_org -v
```

Expected: `ImportError: cannot import name 'RecipeResult'`

- [ ] **Step 3: Add RecipeResult, fetch_html, and extract_recipe to extractor.py**

Insert near the top of `extractor.py` (after imports, before `parse_duration`):

```python
@dataclass
class RecipeResult:
    schema: dict
    markdown: str
    strategy: Literal["schema_org", "heuristic"]
    title: str
```

Append to the bottom of `extractor.py`:

```python
def fetch_html(url: str) -> str:
    """Fetch URL with a browser User-Agent. Raises on non-2xx."""
    resp = requests.get(url, headers={"User-Agent": BROWSER_UA}, timeout=15)
    resp.raise_for_status()
    return resp.text


def extract_recipe(url: str) -> RecipeResult:
    """Main entry point: fetch URL, extract, normalise, render."""
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    raw = extract_schema_org(soup)
    if raw:
        strategy: Literal["schema_org", "heuristic"] = "schema_org"
    else:
        raw = extract_heuristic(soup)
        strategy = "heuristic"

    if not raw or not raw.get("name"):
        raise ValueError(f"Could not extract recipe from {url}")

    normalized = normalize_recipe(raw)
    md = recipe_to_markdown(normalized)
    return RecipeResult(
        schema=normalized,
        markdown=md,
        strategy=strategy,
        title=normalized.get("name", ""),
    )
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/test_extractor.py -v
```

Expected: 24 passed.

- [ ] **Step 5: Commit**

```bash
git add extractor.py tests/test_extractor.py
git commit -m "feat: extract_recipe orchestration, fetch, RecipeResult dataclass"
```

---

## Task 8: main.py — FastAPI web server

**Files:**
- Create: `main.py`

No new tests needed — FastAPI's automatic request validation covers the API contract; extractor logic is already tested.

- [ ] **Step 1: Create main.py**

```python
import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests

from extractor import extract_recipe, RecipeResult

app = FastAPI(title="Recipe Extractor")


class ExtractRequest(BaseModel):
    url: str


@app.post("/extract")
def extract(req: ExtractRequest):
    try:
        result: RecipeResult = extract_recipe(req.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except requests.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "schema": result.schema,
        "markdown": result.markdown,
        "strategy": result.strategy,
        "title": result.title,
    }


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
```

- [ ] **Step 2: Verify the server starts**

```bash
python main.py &
sleep 2
curl -s http://localhost:8000/  # should return HTML (404 until index.html exists is OK)
kill %1
```

Expected: server starts without import errors. A 404 for `/` is fine — `static/index.html` doesn't exist yet.

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: FastAPI server with POST /extract and static file serving"
```

---

## Task 9: cli.py — command-line interface

**Files:**
- Create: `cli.py`

- [ ] **Step 1: Create cli.py**

```python
#!/usr/bin/env python3
"""Recipe Extractor CLI.

Usage:
    python cli.py <url>              # print markdown to stdout
    python cli.py <url> --json       # print JSON to stdout
    python cli.py <url> --out recipe.md   # write markdown to file
    python cli.py <url> --out recipe.json # write JSON to file
"""
import argparse
import json
import sys
import requests

from extractor import extract_recipe


def slugify(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main():
    parser = argparse.ArgumentParser(description="Extract a recipe from a URL")
    parser.add_argument("url", help="URL of the recipe page")
    parser.add_argument("--json", action="store_true", help="Output full JSON instead of Markdown")
    parser.add_argument("--out", metavar="FILE", help="Write output to FILE (.md or .json)")
    args = parser.parse_args()

    try:
        result = extract_recipe(args.url)
    except (ValueError, requests.HTTPError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine output format
    if args.out and args.out.endswith(".json"):
        content = json.dumps(
            {"schema": result.schema, "markdown": result.markdown,
             "strategy": result.strategy, "title": result.title},
            indent=2,
        )
    elif args.json:
        content = json.dumps(
            {"schema": result.schema, "markdown": result.markdown,
             "strategy": result.strategy, "title": result.title},
            indent=2,
        )
    else:
        content = result.markdown

    if args.out:
        with open(args.out, "w") as f:
            f.write(content)
        print(f"Saved to {args.out}")
    else:
        print(content)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify CLI help works**

```bash
python cli.py --help
```

Expected output includes `url`, `--json`, `--out`.

- [ ] **Step 3: Commit**

```bash
git add cli.py
git commit -m "feat: CLI with markdown/json output and --out file option"
```

---

## Task 10: static/index.html — frontend

**Files:**
- Create: `static/index.html`

- [ ] **Step 1: Create static/index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Recipe Extractor</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --orange: #f97316;
      --orange-light: #fff7ed;
      --orange-dark: #ea6c0a;
      --green: #16a34a;
      --amber: #d97706;
      --grey: #6b7280;
      --radius: 10px;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 16px;
      line-height: 1.6;
      background: #fafafa;
      color: #111;
      padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);
    }

    header {
      background: var(--orange);
      color: #fff;
      padding: 1rem 1.25rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    header h1 { font-size: 1.2rem; font-weight: 700; }

    .container { max-width: 680px; margin: 0 auto; padding: 1.25rem; }

    .input-row {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1.25rem;
    }

    input[type=url] {
      flex: 1;
      padding: 0.65rem 0.9rem;
      font-size: 16px; /* prevents iOS auto-zoom */
      border: 1.5px solid #d1d5db;
      border-radius: var(--radius);
      outline: none;
    }

    input[type=url]:focus { border-color: var(--orange); }

    button {
      padding: 0.65rem 1.1rem;
      background: var(--orange);
      color: #fff;
      border: none;
      border-radius: var(--radius);
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
    }

    button:hover { background: var(--orange-dark); }
    button:disabled { opacity: 0.6; cursor: not-allowed; }

    /* Spinner */
    .spinner {
      display: none;
      width: 36px; height: 36px;
      border: 4px solid #e5e7eb;
      border-top-color: var(--orange);
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
      margin: 2rem auto;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* Error */
    .error-box {
      display: none;
      background: #fef2f2;
      border: 1.5px solid #fca5a5;
      border-radius: var(--radius);
      padding: 0.9rem 1rem;
      color: #b91c1c;
      margin-bottom: 1rem;
    }

    /* Recipe card */
    .recipe-card { display: none; }

    .recipe-header { margin-bottom: 1rem; }

    .recipe-title {
      font-size: 1.5rem;
      font-weight: 700;
      margin-bottom: 0.4rem;
    }

    .meta-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
      margin-bottom: 0.75rem;
    }

    .chip {
      background: var(--orange-light);
      color: var(--orange-dark);
      border-radius: 999px;
      padding: 0.2rem 0.75rem;
      font-size: 0.85rem;
      font-weight: 500;
    }

    .strategy-badge {
      display: inline-block;
      border-radius: 999px;
      padding: 0.2rem 0.75rem;
      font-size: 0.82rem;
      font-weight: 600;
    }
    .strategy-badge.schema  { background: #dcfce7; color: var(--green); }
    .strategy-badge.heuristic { background: #fef3c7; color: var(--amber); }

    .action-row {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1.25rem;
      flex-wrap: wrap;
    }

    .action-btn {
      background: #fff;
      color: #374151;
      border: 1.5px solid #d1d5db;
      font-size: 0.9rem;
      font-weight: 500;
    }
    .action-btn:hover { background: #f3f4f6; }

    .section-title {
      font-size: 1.1rem;
      font-weight: 700;
      margin: 1.25rem 0 0.5rem;
      padding-bottom: 0.25rem;
      border-bottom: 2px solid var(--orange-light);
    }

    .ingredient-list { list-style: disc; padding-left: 1.4rem; }
    .ingredient-list li { margin-bottom: 0.25rem; }

    .step-list { list-style: none; padding: 0; }
    .step-list li {
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
      margin-bottom: 0.75rem;
    }

    .step-badge {
      flex-shrink: 0;
      width: 1.8rem; height: 1.8rem;
      border-radius: 50%;
      background: var(--orange);
      color: #fff;
      font-weight: 700;
      font-size: 0.85rem;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .section-heading {
      font-size: 1rem;
      font-weight: 600;
      margin: 1rem 0 0.5rem;
      color: var(--grey);
    }
  </style>
</head>
<body>

<header>
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 1 0 0 20A10 10 0 0 0 12 2z"/><path d="M12 8v4l3 3"/></svg>
  <h1>Recipe Extractor</h1>
</header>

<div class="container">
  <div class="input-row">
    <input type="url" id="urlInput" placeholder="Paste a recipe URL…" autocomplete="off">
    <button id="extractBtn">Get Recipe</button>
  </div>

  <div class="spinner" id="spinner"></div>
  <div class="error-box" id="errorBox"></div>
  <div class="recipe-card" id="recipeCard"></div>
</div>

<script>
  const urlInput = document.getElementById('urlInput');
  const extractBtn = document.getElementById('extractBtn');
  const spinner = document.getElementById('spinner');
  const errorBox = document.getElementById('errorBox');
  const recipeCard = document.getElementById('recipeCard');

  let currentResult = null;

  function slugify(text) {
    return text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    // execCommand fallback for older Safari
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    return Promise.resolve();
  }

  function showError(msg) {
    errorBox.textContent = msg;
    errorBox.style.display = 'block';
    recipeCard.style.display = 'none';
    spinner.style.display = 'none';
  }

  function renderMeta(data) {
    const chips = [];
    const s = data.schema;
    if (s.author) {
      const name = Array.isArray(s.author) ? s.author.join(', ') : s.author;
      chips.push(name);
    }
    if (s.recipeYield) chips.push('Yield: ' + s.recipeYield);
    if (s.prepTime)   chips.push('Prep: ' + parseDuration(s.prepTime));
    if (s.cookTime)   chips.push('Cook: ' + parseDuration(s.cookTime));
    if (s.totalTime)  chips.push('Total: ' + parseDuration(s.totalTime));
    return chips.map(c => `<span class="chip">${esc(c)}</span>`).join('');
  }

  function parseDuration(iso) {
    const m = iso.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
    if (!m) return iso;
    const h = parseInt(m[1] || 0), min = parseInt(m[2] || 0);
    const parts = [];
    if (h)   parts.push(h + ' hr');
    if (min) parts.push(min + ' min');
    return parts.join(' ') || iso;
  }

  function esc(str) {
    return String(str)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function renderInstructions(instructions) {
    if (!instructions || !instructions.length) return '';
    const first = instructions[0];
    if (first && first['@type'] === 'HowToSection') {
      return instructions.map(sec => {
        const steps = (sec.itemListElement || []).map((step, i) => {
          const text = typeof step === 'object' ? step.text : step;
          return `<li><span class="step-badge">${i+1}</span><span>${esc(text)}</span></li>`;
        }).join('');
        return `<p class="section-heading">${esc(sec.name || 'Section')}</p><ol class="step-list">${steps}</ol>`;
      }).join('');
    }
    const steps = instructions.map((step, i) => {
      const text = typeof step === 'object' ? (step.text || '') : step;
      return `<li><span class="step-badge">${i+1}</span><span>${esc(text)}</span></li>`;
    }).join('');
    return `<ol class="step-list">${steps}</ol>`;
  }

  function renderRecipe(data) {
    const s = data.schema;
    const badgeClass = data.strategy === 'schema_org' ? 'schema' : 'heuristic';
    const badgeLabel = data.strategy === 'schema_org' ? '✓ Schema.org' : '⚙ Heuristic';

    const ings = (s.recipeIngredient || [])
      .map(i => `<li>${esc(i)}</li>`).join('');

    recipeCard.innerHTML = `
      <div class="recipe-header">
        <div class="recipe-title">${esc(data.title)}</div>
        <div class="meta-chips">
          ${renderMeta(data)}
          <span class="strategy-badge ${badgeClass}">${badgeLabel}</span>
        </div>
      </div>
      <div class="action-row">
        <button class="action-btn" id="copyBtn">Copy for Notes</button>
        <button class="action-btn" id="downloadBtn">Download JSON</button>
      </div>
      ${ings ? `<div class="section-title">Ingredients</div><ul class="ingredient-list">${ings}</ul>` : ''}
      ${s.recipeInstructions ? `<div class="section-title">Instructions</div>${renderInstructions(s.recipeInstructions)}` : ''}
    `;

    recipeCard.style.display = 'block';

    document.getElementById('copyBtn').addEventListener('click', () => {
      copyToClipboard(data.markdown).then(() => {
        const btn = document.getElementById('copyBtn');
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = 'Copy for Notes'; }, 2000);
      });
    });

    document.getElementById('downloadBtn').addEventListener('click', () => {
      const slug = slugify(data.title || 'recipe');
      const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = slug + '.json';
      a.click();
    });
  }

  async function doExtract() {
    const url = urlInput.value.trim();
    if (!url) { urlInput.focus(); return; }

    extractBtn.disabled = true;
    spinner.style.display = 'block';
    errorBox.style.display = 'none';
    recipeCard.style.display = 'none';

    try {
      const resp = await fetch('/extract', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({url}),
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || `Server error ${resp.status}`);
      }
      currentResult = data;
      spinner.style.display = 'none';
      renderRecipe(data);
    } catch (err) {
      showError(err.message || 'Extraction failed. Check the URL and try again.');
    } finally {
      extractBtn.disabled = false;
    }
  }

  extractBtn.addEventListener('click', doExtract);
  urlInput.addEventListener('keydown', e => { if (e.key === 'Enter') doExtract(); });
</script>
</body>
</html>
```

- [ ] **Step 2: Start the server and verify the UI loads**

```bash
python main.py &
sleep 2
open http://localhost:8000
```

Expected: page loads with URL input and "Get Recipe" button.

```bash
kill %1
```

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "feat: single-file mobile-first frontend with clipboard and JSON download"
```

---

## Task 11: render.yaml and README.md

**Files:**
- Create: `render.yaml`
- Create: `README.md`

- [ ] **Step 1: Create render.yaml**

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

- [ ] **Step 2: Create README.md**

```markdown
# Recipe Extractor

Paste any recipe URL and get back structured ingredients, instructions, and a clean Markdown copy — ready for Apple Notes, Obsidian, or wherever you keep things.

## What it does

1. Fetches the page with a browser User-Agent
2. **Strategy 1:** Looks for Schema.org Recipe data in `<script type="application/ld+json">` tags
3. **Strategy 2 (fallback):** Scrapes the DOM using class-name patterns for popular recipe plugins (WPRM, Tasty, Mediavine) and generic heading traversal
4. Returns JSON `{schema, markdown, strategy, title}` — also shown in a clean web UI

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

## Deploy to Render

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your repo — Render will detect `render.yaml` and configure automatically
4. Click **Deploy**

The free tier spins down after inactivity; first request after sleep may take ~30 s.
```

- [ ] **Step 3: Commit**

```bash
git add render.yaml README.md
git commit -m "chore: add render.yaml and README"
```

---

## Task 12: GitHub push

**Files:** none (git operations only)

- [ ] **Step 1: Final test run**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 2: Create GitHub repo and push**

```bash
gh repo create mrpfisher/recipe-extractor --public --source=. --remote=origin --push
```

Expected: repo created and all commits pushed. Output includes the GitHub URL.

- [ ] **Step 3: Verify**

```bash
gh repo view mrpfisher/recipe-extractor
```

Expected: repo details shown with correct name and visibility.
