import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
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


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
