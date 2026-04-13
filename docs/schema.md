# Recipe Schema Reference

This document describes the structured data formats this tool understands, the fields we extract, and what has been observed across real recipe sites.

---

## Schema.org Recipe (`@type: Recipe`)

[Schema.org/Recipe](https://schema.org/Recipe) is the standard vocabulary for structured recipe data. Most recipe sites embed it in their HTML as a `<script type="application/ld+json">` block so that Google, Bing, and other search engines can index it.

### Standard specification

- Full spec: https://schema.org/Recipe
- Google's requirements & rich-result docs: https://developers.google.com/search/docs/appearance/structured-data/recipe

### Common ld+json shapes

**Direct object** (most common):
```json
{
  "@context": "https://schema.org",
  "@type": "Recipe",
  "name": "Chocolate Cake",
  "recipeIngredient": ["2 cups flour", "1 cup sugar"]
}
```

**`@graph` wrapper** (used by Yoast SEO and similar WordPress plugins):
```json
{
  "@context": "https://schema.org",
  "@graph": [
    { "@type": "WebPage", ... },
    { "@type": "Recipe", "name": "Chocolate Cake", ... }
  ]
}
```

**List root** (less common, some older plugins):
```json
[
  { "@type": "WebPage", ... },
  { "@type": "Recipe", "name": "Chocolate Cake", ... }
]
```

**`@type` as a list** (valid JSON-LD — a node can have multiple types):
```json
{ "@type": ["Recipe", "Thing"], "name": "Chocolate Cake", ... }
```

All four are handled by `extract_schema_org()` in `extractor.py`.

---

## Fields we extract

### Kept by `normalize_recipe()`

| Field | Type | Example |
|---|---|---|
| `name` | string | `"Instant Pot Brisket"` |
| `author` | string, Person dict, or list | `{"@type": "Person", "name": "Urvashi"}` → `"Urvashi"` |
| `description` | string | `"An easy weeknight dinner..."` |
| `image` | string or list of strings | URL(s) to recipe photo |
| `recipeYield` | string or list | `"8"`, `"8 servings"`, `["8", "8 servings"]` → first element taken |
| `prepTime` | ISO 8601 duration | `"PT10M"` → `"10 min"` |
| `cookTime` | ISO 8601 duration | `"PT1H10M"` → `"1 hr 10 min"` |
| `totalTime` | ISO 8601 duration | `"PT1H20M"` → `"1 hr 20 min"` |
| `recipeIngredient` | list of strings | `["2 cups flour", "1 tsp salt"]` |
| `recipeInstructions` | list of HowToStep or HowToSection | see below |
| `recipeCategory` | string or list | `"Main Courses"`, `["Dinner"]` |
| `recipeCuisine` | string or list | `"American"`, `["Italian"]` |
| `keywords` | comma-separated string | `"brisket, instant pot, pressure cooker"` |
| `nutrition` | NutritionInformation dict | see below |

### Stripped by `normalize_recipe()` (present in raw ld+json but not kept)

| Field | Why excluded |
|---|---|
| `@type`, `@id`, `@context` | Internal JSON-LD metadata |
| `aggregateRating` | Rating/review data, not part of the recipe itself |
| `review` | User review content |
| `datePublished`, `dateModified` | Publication metadata |
| `video` | Video embeds |
| `isPartOf`, `mainEntityOfPage` | Page graph relationships |
| `url` | We track provenance separately in `RecipeResult.url` |

---

## recipeInstructions formats

The spec allows several shapes. We handle all of them.

**Flat list of HowToStep** (most common):
```json
"recipeInstructions": [
  { "@type": "HowToStep", "text": "Preheat oven to 350°F." },
  { "@type": "HowToStep", "text": "Mix dry ingredients." }
]
```

**HowToSection** (used when steps are grouped, e.g. "For the Sauce", "For the Pressure Cooker"):
```json
"recipeInstructions": [
  {
    "@type": "HowToSection",
    "name": "For the Pressure Cooker",
    "itemListElement": [
      { "@type": "HowToStep", "text": "Season the meat." },
      { "@type": "HowToStep", "text": "Cook at high pressure for 35 minutes." }
    ]
  },
  {
    "@type": "HowToSection",
    "name": "For the Slow Cooker",
    "itemListElement": [
      { "@type": "HowToStep", "text": "Cook on low for 8-9 hours." }
    ]
  }
]
```

Rendered in Markdown as `### Section Name` headings with per-section numbered steps.

**Plain strings** (uncommon, older sites):
```json
"recipeInstructions": ["Mix everything.", "Bake 45 minutes."]
```

---

## nutrition (NutritionInformation)

Schema.org type: https://schema.org/NutritionInformation

```json
"nutrition": {
  "@type": "NutritionInformation",
  "calories": "200 kcal",
  "carbohydrateContent": "5 g",
  "proteinContent": "24 g",
  "fatContent": "8 g",
  "saturatedFatContent": "2 g",
  "fiberContent": "1 g",
  "sugarContent": "2 g",
  "sodiumContent": "450 mg"
}
```

Fields we surface (in markdown and UI): `calories`, `carbohydrateContent`, `proteinContent`, `fatContent`, `saturatedFatContent`, `fiberContent`, `sugarContent`, `sodiumContent`.

---

## WPRM — WP Recipe Maker

[WP Recipe Maker](https://bootstrapped.ventures/wp-recipe-maker/) is the most widely deployed recipe plugin for WordPress. It emits Schema.org ld+json (Strategy 1 picks this up) **and** renders a rich DOM card (Strategy 2 can scrape this as a fallback).

### WPRM ld+json

WPRM outputs a well-formed Schema.org Recipe object. Our Strategy 1 handles it cleanly. Notable WPRM behaviours:

- `recipeYield` is often a plain integer string: `"8"` (not `"8 servings"`)
- `recipeInstructions` uses `HowToSection` when the recipe author has grouped steps
- Ingredient groups (e.g. "For the Sauce") appear **only** in the DOM — the ld+json flattens all ingredients into a single `recipeIngredient` list
- Nutrition is emitted as a `NutritionInformation` node when the author fills it in

### WPRM DOM structure (Strategy 2 fallback)

When ld+json is absent or malformed, we look for these class patterns:

| Purpose | Class pattern |
|---|---|
| Container | `.wprm-recipe-container` or `.wprm-recipe` |
| Name | `.wprm-recipe-name` |
| Ingredient | `.wprm-recipe-ingredient` (one per ingredient) |
| Instruction | `.wprm-recipe-instruction` (one per step) |

**Limitation:** The DOM fallback flattens ingredient groups, and does not currently capture nutrition from the DOM.

Real-world WPRM container ID: `#wprm-recipe-container-{post_id}` (e.g. `#wprm-recipe-container-7552`).

---

## Other recipe plugins

### Tasty Recipes

- Used by Pinch of Yum and other food blogs
- Also emits Schema.org ld+json
- DOM class prefix: `tasty-recipes-*`
- Container: `.tasty-recipes`

Reference: https://www.tastyfoodplugins.com/

### Mediavine Create (mv-recipe)

- Used on Mediavine-monetised sites
- Emits Schema.org ld+json
- DOM class prefix: `mv-recipe-*`
- Real-world container class: `mv-recipe-card` (note: our regex matches `mv-recipe` or `mv-recipe-container`; `mv-recipe-card` is a known gap)

### Ziplist / ZipRecipes (legacy)

- Older plugin, largely retired; class prefix `zlrecipe-*`
- Not currently handled by our heuristic fallback

---

## Observed field coverage across sites

| Site / Plugin | ld+json | Nutrition | HowToSection | Notes |
|---|---|---|---|---|
| Two Sleevers (WPRM) | ✅ | ✅ | ✅ | Ingredients not grouped in ld+json |
| Pinch of Yum (Tasty) | ✅ | ✅ | sometimes | |
| NYT Cooking | ✅ | sometimes | ❌ | Flat step list |
| Serious Eats | ✅ | ❌ | sometimes | |
| AllRecipes | ✅ | ✅ | ❌ | |
| Food Network | ✅ | ✅ | ❌ | |
| Generic / custom sites | ❌ | ❌ | ❌ | Heuristic fallback used |

---

## ISO 8601 duration parsing

Recipe times are encoded as ISO 8601 durations. We parse hours (`H`) and minutes (`M`):

| Input | Output |
|---|---|
| `PT10M` | `10 min` |
| `PT1H` | `1 hr` |
| `PT1H30M` | `1 hr 30 min` |
| `PT70M` | `1 hr 10 min` |
| `PT` or invalid | original string returned unchanged |

Days (`P1D`) and seconds (`PT30S`) are not currently parsed (rare in recipe data).
