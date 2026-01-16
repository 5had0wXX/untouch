from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"

app = FastAPI(title="P3 Spotter API")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_methods=["*"],
  allow_headers=["*"]
)


@app.get("/")
async def root() -> FileResponse | JSONResponse:
  if INDEX_FILE.exists():
    return FileResponse(INDEX_FILE)
  return JSONResponse(
    status_code=500,
    content={"error": "index.html not found. Place it next to app.py."},
  )


@app.get("/health")
async def health() -> dict:
  return {"status": "ok"}


@app.get("/search")
async def search(
  lat: float = Query(...),
  lon: float = Query(...),
  radius: float = Query(10, ge=1, le=200),
) -> dict:
  leads = [
    {
      "id": "p3-1",
      "title": "Rivergate Freight Terminal",
      "score": 92,
      "lat": lat + 0.02,
      "lon": lon - 0.01,
    },
    {
      "id": "p3-2",
      "title": "Oak Ridge Transit Hub",
      "score": 84,
      "lat": lat - 0.015,
      "lon": lon + 0.018,
    },
    {
      "id": "p3-3",
      "title": "Cedar Point Industrial Park",
      "score": 78,
      "lat": lat + 0.01,
      "lon": lon + 0.022,
    },
  ]
  return {"query": {"lat": lat, "lon": lon, "radius": radius}, "results": leads}


if __name__ == "__main__":
  import uvicorn

  uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
