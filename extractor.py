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
