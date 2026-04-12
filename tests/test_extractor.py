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
