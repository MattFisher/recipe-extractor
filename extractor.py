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


@dataclass
class RecipeResult:
    schema: dict
    markdown: str
    strategy: Literal["schema_org", "heuristic"]
    title: str
    url: str


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


_RECIPE_FIELDS = {
    "name", "author", "description", "image",
    "recipeYield", "prepTime", "cookTime", "totalTime",
    "recipeIngredient", "recipeInstructions",
    "recipeCategory", "recipeCuisine", "keywords",
    "nutrition",
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

    # Bug fix 1: Handle recipeYield as a list (Schema.org allows this)
    if "recipeYield" in out and isinstance(out["recipeYield"], list):
        out["recipeYield"] = out["recipeYield"][0] if out["recipeYield"] else ""
        if out["recipeYield"] == "":
            del out["recipeYield"]

    # Bug fix 2: Remove empty author string that leaked through
    if out.get("author") in ("", []):
        del out["author"]

    return out


def _format_nutrition(nutrition: dict) -> str:
    """Render a NutritionInformation dict as a compact string."""
    mapping = [
        ("calories", "Calories"),
        ("carbohydrateContent", "Carbs"),
        ("proteinContent", "Protein"),
        ("fatContent", "Fat"),
        ("saturatedFatContent", "Sat. fat"),
        ("fiberContent", "Fiber"),
        ("sugarContent", "Sugar"),
        ("sodiumContent", "Sodium"),
    ]
    parts = []
    for key, label in mapping:
        if nutrition.get(key):
            parts.append(f"{label}: {nutrition[key]}")
    return " · ".join(parts)


def recipe_to_markdown(recipe: dict, source_url: str = "") -> str:
    """Render a normalised recipe dict to Markdown."""
    lines = [f"# {recipe.get('name', 'Recipe')}", ""]

    # Description
    if recipe.get("description"):
        lines += [recipe["description"], ""]

    # Meta line: author, yield, times
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

    # Category / cuisine / keywords
    tags = []
    for key in ("recipeCategory", "recipeCuisine"):
        val = recipe.get(key)
        if val:
            if isinstance(val, list):
                tags.extend(val)
            else:
                tags.append(val)
    if recipe.get("keywords"):
        kw = recipe["keywords"]
        tags.extend(k.strip() for k in kw.split(",") if k.strip())
    if tags:
        lines.append("Tags: " + ", ".join(tags))
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

    # Nutrition
    nutrition = recipe.get("nutrition")
    if isinstance(nutrition, dict):
        nut_str = _format_nutrition(nutrition)
        if nut_str:
            lines += ["## Nutrition", "", nut_str, ""]

    if source_url:
        lines += ["", f"*Source: {source_url}*"]

    return "\n".join(lines).strip()


def _find_recipe_in_ldjson(data) -> dict | None:
    """Recursively search parsed ld+json for a Recipe node."""
    if isinstance(data, list):
        for item in data:
            found = _find_recipe_in_ldjson(item)
            if found:
                return found
    elif isinstance(data, dict):
        _type = data.get("@type", "")
        if _type == "Recipe" or (isinstance(_type, list) and "Recipe" in _type):
            return data
        if "@graph" in data:
            for item in data["@graph"]:
                if isinstance(item, dict):
                    _type = item.get("@type", "")
                    if _type == "Recipe" or (isinstance(_type, list) and "Recipe" in _type):
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


def fetch_html(url: str) -> str:
    """Fetch URL with a browser User-Agent. Raises on non-2xx."""
    resp = requests.get(url, headers={"User-Agent": BROWSER_UA}, timeout=15)
    resp.raise_for_status()
    return resp.text


def extract_recipe_from_html(html: str, url: str) -> RecipeResult:
    """Extract a recipe from already-fetched HTML. url is used for provenance only."""
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
    md = recipe_to_markdown(normalized, source_url=url)
    return RecipeResult(
        schema=normalized,
        markdown=md,
        strategy=strategy,
        title=normalized.get("name", ""),
        url=url,
    )


def extract_recipe(url: str) -> RecipeResult:
    """Fetch url and extract recipe. Delegates to extract_recipe_from_html."""
    return extract_recipe_from_html(fetch_html(url), url)
