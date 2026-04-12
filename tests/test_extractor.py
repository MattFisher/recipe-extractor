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


def test_normalize_recipe_yield_list():
    raw = {"name": "Cake", "recipeYield": ["8", "8 servings"]}
    result = normalize_recipe(raw)
    assert result["recipeYield"] == "8"


def test_normalize_author_missing_name():
    raw = {"name": "Cake", "author": {"@type": "Person"}}
    result = normalize_recipe(raw)
    assert "author" not in result


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
