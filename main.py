import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests

from extractor import extract_recipe, extract_recipe_from_html, RecipeResult

FIXTURES_DIR = Path(__file__).parent / "tests" / "fixtures"

app = FastAPI(title="Recipe Extractor")


class ExtractRequest(BaseModel):
    url: str


@app.post("/extract")
def extract(req: ExtractRequest):
    try:
        result: RecipeResult = extract_recipe(req.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (requests.HTTPError, requests.ConnectionError) as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "schema": result.schema,
        "markdown": result.markdown,
        "strategy": result.strategy,
        "title": result.title,
        "url": result.url,
    }


@app.get("/fixture/{name}")
def fixture(name: str):
    """Load a saved HTML fixture from tests/fixtures/ and extract its recipe.
    Used for local development — no network request needed.
    """
    path = FIXTURES_DIR / f"{name}.html"
    if not path.exists():
        available = [p.stem for p in FIXTURES_DIR.glob("*.html")]
        raise HTTPException(status_code=404, detail=f"Fixture '{name}' not found. Available: {available}")
    try:
        result: RecipeResult = extract_recipe_from_html(path.read_text(), url=f"fixture://{name}")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {
        "schema": result.schema,
        "markdown": result.markdown,
        "strategy": result.strategy,
        "title": result.title,
        "url": result.url,
    }


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
