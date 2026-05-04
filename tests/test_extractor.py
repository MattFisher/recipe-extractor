import pytest
import requests
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


def test_extract_schema_org_type_as_list():
    soup = _soup('{"@type": ["Recipe", "Thing"], "name": "Stew"}')
    result = extract_schema_org(soup)
    assert result is not None
    assert result["name"] == "Stew"


from unittest.mock import patch, MagicMock
from extractor import extract_recipe, validate_url, RecipeResult

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
    with patch("extractor.validate_url"), \
         patch("extractor.requests.get", return_value=_mock_response(_LDJSON_HTML)):
        result = extract_recipe("http://example.com/recipe")
    assert isinstance(result, RecipeResult)
    assert result.title == "Mock Cake"
    assert result.strategy == "schema_org"
    assert "# Mock Cake" in result.markdown
    assert isinstance(result.schema, dict)
    assert result.url == "http://example.com/recipe"
    assert "http://example.com/recipe" in result.markdown


def test_extract_recipe_heuristic_fallback():
    with patch("extractor.validate_url"), \
         patch("extractor.requests.get", return_value=_mock_response(_HEURISTIC_HTML)):
        result = extract_recipe("http://example.com/recipe")
    assert result.title == "Mock Soup"
    assert result.strategy == "heuristic"


def test_extract_recipe_http_error():
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.HTTPError("404")
    with patch("extractor.validate_url"), \
         patch("extractor.requests.get", return_value=resp):
        with pytest.raises(requests.HTTPError):
            extract_recipe("http://example.com/404")


# --- validate_url (SSRF protection) ---

def test_validate_url_accepts_public_https():
    # 93.184.216.34 is example.com — IP literal resolves without DNS
    validate_url("https://93.184.216.34/recipe")


def test_validate_url_accepts_public_http():
    validate_url("http://93.184.216.34/recipe")


def test_validate_url_rejects_ftp_scheme():
    with pytest.raises(ValueError, match="http"):
        validate_url("ftp://example.com/recipe")


def test_validate_url_rejects_file_scheme():
    with pytest.raises(ValueError, match="http"):
        validate_url("file:///etc/passwd")


def test_validate_url_rejects_loopback():
    with pytest.raises(ValueError, match="private"):
        validate_url("http://127.0.0.1/recipe")


def test_validate_url_rejects_private_10():
    with pytest.raises(ValueError, match="private"):
        validate_url("http://10.0.0.1/recipe")


def test_validate_url_rejects_private_192_168():
    with pytest.raises(ValueError, match="private"):
        validate_url("http://192.168.1.100/recipe")


def test_validate_url_rejects_link_local():
    # 169.254.169.254 is the AWS instance metadata endpoint
    with pytest.raises(ValueError, match="private"):
        validate_url("http://169.254.169.254/latest/meta-data/")


def test_validate_url_rejects_localhost():
    with pytest.raises(ValueError, match="private"):
        validate_url("http://localhost/recipe")
