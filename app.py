from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="P3 Spotter API")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_methods=["*"],
  allow_headers=["*"]
)


@app.get("/search")
async def search(
  lat: float = Query(...),
  lon: float = Query(...),
  radius: float = Query(10, ge=1, le=200)
):
  leads = [
    {
      "id": "p3-1",
      "title": "Rivergate Freight Terminal",
      "score": 92,
      "lat": lat + 0.02,
      "lon": lon - 0.01
    },
    {
      "id": "p3-2",
      "title": "Oak Ridge Transit Hub",
      "score": 84,
      "lat": lat - 0.015,
      "lon": lon + 0.018
    },
    {
      "id": "p3-3",
      "title": "Cedar Point Industrial Park",
      "score": 78,
      "lat": lat + 0.01,
      "lon": lon + 0.022
    }
  ]
  return {
    "query": {"lat": lat, "lon": lon, "radius": radius},
    "results": leads
  }
