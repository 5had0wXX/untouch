import csv
import hashlib
import json
import math
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser
import requests
from bs4 import BeautifulSoup
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "untouch.db"
CACHE_DIR = BASE_DIR / "cache"
INDEX_FILE = BASE_DIR / "index.html"

DATASET_URL = (
  "https://data.ct.gov/resource/5mzw-sjtu.csv?"
  "$select=address,city,town,county,land_use_desc,owner_name,"
  "acreage,building_sqft,latitude,longitude,property_name"
)
DATASET_FILE = BASE_DIR / "ct_parcels.csv"

RATE_LIMIT_SECONDS = 1.0
CACHE_TTL_SECONDS = 60 * 60 * 24

refresh_lock = threading.Lock()
refresh_status = {
  "state": "idle",
  "last_refresh": None,
  "runtime_seconds": 0,
  "candidates": 0,
  "signals": 0,
  "scores": 0,
  "message": "Not started",
}
last_request_time = 0.0


@dataclass
class Candidate:
  id: int
  name: str
  lat: float
  lon: float
  address: str
  town: str
  county: str
  acres: float
  bldg_sqft: float
  land_use: str
  owner: str
  source: str


def init_storage() -> None:
  CACHE_DIR.mkdir(exist_ok=True)
  conn = sqlite3.connect(DB_PATH)
  try:
    conn.executescript(
      """
      CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        lat REAL,
        lon REAL,
        address TEXT,
        town TEXT,
        county TEXT,
        acres REAL,
        bldg_sqft REAL,
        land_use TEXT,
        owner TEXT,
        source TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
      );

      CREATE TABLE IF NOT EXISTS signals (
        candidate_id INTEGER,
        signal_type TEXT,
        signal_value TEXT,
        url TEXT,
        observed_at TEXT
      );

      CREATE TABLE IF NOT EXISTS scores (
        candidate_id INTEGER,
        score_total INTEGER,
        score_breakdown_json TEXT,
        updated_at TEXT
      );

      CREATE INDEX IF NOT EXISTS idx_candidates_town ON candidates(town);
      CREATE INDEX IF NOT EXISTS idx_candidates_coords ON candidates(lat, lon);
      CREATE INDEX IF NOT EXISTS idx_signals_candidate ON signals(candidate_id);
      CREATE INDEX IF NOT EXISTS idx_scores_candidate ON scores(candidate_id);
      """
    )
    conn.commit()
  finally:
    conn.close()


def db_connection() -> sqlite3.Connection:
  conn = sqlite3.connect(DB_PATH)
  conn.row_factory = sqlite3.Row
  return conn


def cached_request(url: str) -> str:
  global last_request_time
  CACHE_DIR.mkdir(exist_ok=True)
  key = hashlib.sha256(url.encode("utf-8")).hexdigest()
  cache_file = CACHE_DIR / f"{key}.json"
  if cache_file.exists():
    data = json.loads(cache_file.read_text())
    if time.time() - data["timestamp"] < CACHE_TTL_SECONDS:
      return data["text"]

  wait = RATE_LIMIT_SECONDS - (time.time() - last_request_time)
  if wait > 0:
    time.sleep(wait)
  headers = {
    "User-Agent": "UntouchP3Recon/1.0 (public data; contact local user)"
  }
  response = requests.get(url, headers=headers, timeout=30)
  response.raise_for_status()
  last_request_time = time.time()
  cache_file.write_text(json.dumps({"timestamp": time.time(), "text": response.text}))
  return response.text


def download_dataset() -> None:
  if DATASET_FILE.exists():
    return
  try:
    text = cached_request(DATASET_URL)
    DATASET_FILE.write_text(text)
  except Exception:
    return


def normalize_land_use(land_use: str) -> str:
  return land_use.strip().lower()


def allowed_land_use(land_use: str) -> bool:
  normalized = normalize_land_use(land_use)
  allowed_keywords = ["industrial", "commercial", "institutional", "warehouse", "utility"]
  blocked_keywords = [
    "residential",
    "single family",
    "multi family",
    "restaurant",
    "retail",
    "condo",
    "apartment",
    "hotel",
  ]
  if any(keyword in normalized for keyword in blocked_keywords):
    return False
  return any(keyword in normalized for keyword in allowed_keywords)


def parse_float(value: Any) -> float:
  try:
    return float(value)
  except (TypeError, ValueError):
    return 0.0


def load_candidates_from_csv(path: Path) -> list[dict[str, Any]]:
  if not path.exists():
    return []
  candidates: list[dict[str, Any]] = []
  with path.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle)
    for row in reader:
      land_use = row.get("land_use_desc") or row.get("land_use") or ""
      if land_use and not allowed_land_use(land_use):
        continue
      acres = parse_float(row.get("acreage") or row.get("acres"))
      bldg_sqft = parse_float(row.get("building_sqft") or row.get("bldg_sqft"))
      lat = parse_float(row.get("latitude") or row.get("lat"))
      lon = parse_float(row.get("longitude") or row.get("lon"))
      if not lat or not lon:
        continue
      candidates.append(
        {
          "name": row.get("property_name") or row.get("name") or "CT Parcel",
          "lat": lat,
          "lon": lon,
          "address": row.get("address") or "",
          "town": row.get("town") or row.get("city") or "",
          "county": row.get("county") or "",
          "acres": acres,
          "bldg_sqft": bldg_sqft,
          "land_use": land_use,
          "owner": row.get("owner_name") or row.get("owner") or "",
          "source": "CT Open Data",
        }
      )
  return candidates


def seed_candidates() -> list[dict[str, Any]]:
  return [
    {
      "name": "Hartford Industrial Park",
      "lat": 41.7564,
      "lon": -72.6851,
      "address": "20 Meadow Rd",
      "town": "Hartford",
      "county": "Hartford",
      "acres": 18.5,
      "bldg_sqft": 120000,
      "land_use": "Industrial",
      "owner": "Public Works",
      "source": "CT GIS sample",
    },
    {
      "name": "New Britain Logistics Hub",
      "lat": 41.6765,
      "lon": -72.7795,
      "address": "175 Fenn Rd",
      "town": "New Britain",
      "county": "Hartford",
      "acres": 22.3,
      "bldg_sqft": 98000,
      "land_use": "Industrial",
      "owner": "Logistics Authority",
      "source": "CT GIS sample",
    },
    {
      "name": "Windsor Commerce Campus",
      "lat": 41.8521,
      "lon": -72.6449,
      "address": "800 Day Hill Rd",
      "town": "Windsor",
      "county": "Hartford",
      "acres": 34.2,
      "bldg_sqft": 210000,
      "land_use": "Commercial",
      "owner": "State Holdings",
      "source": "CT GIS sample",
    },
    {
      "name": "East Hartford Rail Yard",
      "lat": 41.7802,
      "lon": -72.6122,
      "address": "310 Tolland St",
      "town": "East Hartford",
      "county": "Hartford",
      "acres": 27.8,
      "bldg_sqft": 150000,
      "land_use": "Industrial",
      "owner": "Transit Authority",
      "source": "CT GIS sample",
    },
    {
      "name": "Manchester Technology Park",
      "lat": 41.7789,
      "lon": -72.523,
      "address": "500 Main St",
      "town": "Manchester",
      "county": "Hartford",
      "acres": 19.1,
      "bldg_sqft": 88000,
      "land_use": "Industrial",
      "owner": "Municipal Holdings",
      "source": "CT GIS sample",
    },
    {
      "name": "Enfield Distribution Center",
      "lat": 41.9762,
      "lon": -72.5917,
      "address": "150 Freshwater Blvd",
      "town": "Enfield",
      "county": "Hartford",
      "acres": 31.6,
      "bldg_sqft": 190000,
      "land_use": "Commercial",
      "owner": "Regional Logistics",
      "source": "CT GIS sample",
    },
  ]


def upsert_candidates(records: list[dict[str, Any]]) -> None:
  conn = db_connection()
  try:
    conn.execute("DELETE FROM candidates")
    for record in records:
      conn.execute(
        """
        INSERT INTO candidates
          (name, lat, lon, address, town, county, acres, bldg_sqft, land_use, owner, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
          record["name"],
          record["lat"],
          record["lon"],
          record["address"],
          record["town"],
          record["county"],
          record["acres"],
          record["bldg_sqft"],
          record["land_use"],
          record["owner"],
          record["source"],
        ),
      )
    conn.commit()
  finally:
    conn.close()


def dedupe_candidates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
  seen = set()
  unique: list[dict[str, Any]] = []
  for record in records:
    key = (
      record["name"].lower(),
      record["address"].lower(),
      record["town"].lower(),
    )
    if key in seen:
      continue
    seen.add(key)
    unique.append(record)
  return unique


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
  radius = 3958.8
  lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
  lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
  dlat = lat2_rad - lat1_rad
  dlon = lon2_rad - lon1_rad
  a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(
    dlon / 2
  ) ** 2
  c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
  return radius * c


def news_signals(candidate: Candidate) -> list[dict[str, str]]:
  query = f"{candidate.name} {candidate.town} redevelopment OR facility"
  url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}"
  signals = []
  try:
    feed = feedparser.parse(cached_request(url))
    for entry in feed.entries[:3]:
      signals.append(
        {
          "signal_type": "news",
          "signal_value": entry.title,
          "url": entry.link,
        }
      )
  except Exception:
    return []
  return signals


def warn_signals(candidate: Candidate) -> list[dict[str, str]]:
  url = "https://www.ctdol.state.ct.us/warn.htm"
  signals = []
  try:
    text = cached_request(url)
    soup = BeautifulSoup(text, "html.parser")
    page_text = soup.get_text(" ")
    if candidate.town.lower() in page_text.lower():
      signals.append(
        {
          "signal_type": "warn",
          "signal_value": f"WARN notice mentions {candidate.town}",
          "url": url,
        }
      )
  except Exception:
    return []
  return signals


def foreclosure_signals(candidate: Candidate) -> list[dict[str, str]]:
  query = f"{candidate.town} CT tax sale foreclosure industrial"
  url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}"
  signals = []
  try:
    feed = feedparser.parse(cached_request(url))
    for entry in feed.entries[:2]:
      signals.append(
        {
          "signal_type": "tax_sale",
          "signal_value": entry.title,
          "url": entry.link,
        }
      )
  except Exception:
    return []
  return signals


def score_candidate(candidate: Candidate, signals: list[dict[str, str]]) -> dict[str, Any]:
  breakdown = {
    "parcel": 0,
    "news": 0,
    "warn": 0,
    "tax_sale": 0,
    "size": 0,
  }
  for signal in signals:
    signal_type = signal["signal_type"]
    if signal_type in ("parcel_land_use", "parcel_size"):
      breakdown["parcel"] += 6
    else:
      breakdown[signal_type] = breakdown.get(signal_type, 0) + 10

  if candidate.acres >= 25:
    breakdown["size"] += 15
  elif candidate.acres >= 10:
    breakdown["size"] += 8

  if candidate.bldg_sqft >= 150000:
    breakdown["size"] += 15
  elif candidate.bldg_sqft >= 50000:
    breakdown["size"] += 8

  total = sum(breakdown.values())
  return {"total": total, "breakdown": breakdown}


def write_signals_and_scores(candidates: list[Candidate]) -> None:
  conn = db_connection()
  try:
    conn.execute("DELETE FROM signals")
    conn.execute("DELETE FROM scores")
    total_signals = 0
    for candidate in candidates:
      base_signals = [
        {
          "signal_type": "parcel_land_use",
          "signal_value": f"Land use: {candidate.land_use}",
          "url": candidate.source,
        },
        {
          "signal_type": "parcel_size",
          "signal_value": f"{candidate.acres} acres / {candidate.bldg_sqft} sqft",
          "url": candidate.source,
        },
      ]
      signals = base_signals + news_signals(candidate) + warn_signals(candidate) + foreclosure_signals(candidate)
      observed_at = datetime.now(timezone.utc).isoformat()
      for signal in signals:
        conn.execute(
          "INSERT INTO signals (candidate_id, signal_type, signal_value, url, observed_at) VALUES (?, ?, ?, ?, ?)",
          (
            candidate.id,
            signal["signal_type"],
            signal["signal_value"],
            signal["url"],
            observed_at,
          ),
        )
      score_payload = score_candidate(candidate, signals)
      conn.execute(
        "INSERT INTO scores (candidate_id, score_total, score_breakdown_json, updated_at) VALUES (?, ?, ?, ?)",
        (
          candidate.id,
          score_payload["total"],
          json.dumps(score_payload["breakdown"]),
          observed_at,
        ),
      )
      total_signals += len(signals)
    conn.commit()
  finally:
    conn.close()

  refresh_status["signals"] = total_signals


def fetch_candidates_from_db() -> list[Candidate]:
  conn = db_connection()
  try:
    rows = conn.execute("SELECT * FROM candidates").fetchall()
    return [
      Candidate(
        id=row["id"],
        name=row["name"],
        lat=row["lat"],
        lon=row["lon"],
        address=row["address"],
        town=row["town"],
        county=row["county"],
        acres=row["acres"],
        bldg_sqft=row["bldg_sqft"],
        land_use=row["land_use"],
        owner=row["owner"],
        source=row["source"],
      )
      for row in rows
    ]
  finally:
    conn.close()


def refresh_job(min_acres: float, min_bldg_sqft: float) -> None:
  start = time.time()
  refresh_status.update(
    {
      "state": "running",
      "message": "Refreshing candidate universe",
      "runtime_seconds": 0,
    }
  )

  download_dataset()
  records = load_candidates_from_csv(DATASET_FILE)
  if not records:
    records = seed_candidates()

  filtered = [
    record
    for record in records
    if record["acres"] >= min_acres and record["bldg_sqft"] >= min_bldg_sqft
  ]
  deduped = dedupe_candidates(filtered)
  upsert_candidates(deduped)

  candidates = fetch_candidates_from_db()
  write_signals_and_scores(candidates)

  runtime = round(time.time() - start, 2)
  refresh_status.update(
    {
      "state": "idle",
      "last_refresh": datetime.now(timezone.utc).isoformat(),
      "runtime_seconds": runtime,
      "candidates": len(candidates),
      "scores": len(candidates),
      "message": "Refresh complete",
    }
  )


def ensure_refresh(background_tasks: BackgroundTasks, min_acres: float, min_bldg_sqft: float) -> None:
  if refresh_lock.locked():
    return

  def wrapped() -> None:
    with refresh_lock:
      refresh_job(min_acres=min_acres, min_bldg_sqft=min_bldg_sqft)

  background_tasks.add_task(wrapped)


def candidate_signals(candidate_id: int) -> list[dict[str, Any]]:
  conn = db_connection()
  try:
    rows = conn.execute(
      "SELECT signal_type, signal_value, url, observed_at FROM signals WHERE candidate_id = ?",
      (candidate_id,),
    ).fetchall()
    return [dict(row) for row in rows]
  finally:
    conn.close()


def candidate_score(candidate_id: int) -> dict[str, Any]:
  conn = db_connection()
  try:
    row = conn.execute(
      "SELECT score_total, score_breakdown_json FROM scores WHERE candidate_id = ?",
      (candidate_id,),
    ).fetchone()
    if not row:
      return {"score_total": 0, "breakdown": {}}
    return {
      "score_total": row["score_total"],
      "breakdown": json.loads(row["score_breakdown_json"]),
    }
  finally:
    conn.close()


def search_candidates(
  lat: float,
  lon: float,
  radius_miles: float,
  min_acres: float,
  min_bldg_sqft: float,
  min_score: int,
) -> list[dict[str, Any]]:
  conn = db_connection()
  try:
    rows = conn.execute("SELECT * FROM candidates").fetchall()
  finally:
    conn.close()

  results = []
  for row in rows:
    distance = haversine_miles(lat, lon, row["lat"], row["lon"])
    if distance > radius_miles:
      continue
    if row["acres"] < min_acres or row["bldg_sqft"] < min_bldg_sqft:
      continue
    score = candidate_score(row["id"])
    if score["score_total"] < min_score:
      continue
    signals = candidate_signals(row["id"])
    if len({signal["signal_type"] for signal in signals}) < 2:
      continue
    results.append(
      {
        **dict(row),
        "distance_miles": round(distance, 2),
        "score_total": score["score_total"],
        "score_breakdown": score["breakdown"],
        "signals": signals,
      }
    )
  results.sort(key=lambda item: item["score_total"], reverse=True)
  return results


app = FastAPI(title="Untouch P3 Finder")


@app.get("/")
async def index() -> HTMLResponse:
  if not INDEX_FILE.exists():
    raise HTTPException(status_code=500, detail="index.html missing")
  return HTMLResponse(INDEX_FILE.read_text())


@app.get("/api/status")
async def status() -> JSONResponse:
  return JSONResponse(refresh_status)


@app.post("/api/refresh")
async def refresh(background_tasks: BackgroundTasks) -> JSONResponse:
  ensure_refresh(background_tasks, min_acres=10, min_bldg_sqft=50000)
  return JSONResponse({"state": refresh_status["state"], "message": "Refresh queued"})


@app.get("/api/search")
async def search(
  lat: float = Query(...),
  lon: float = Query(...),
  radius_miles: float = Query(25, ge=1, le=200),
  min_acres: float = Query(10),
  min_bldg_sqft: float = Query(50000),
  min_score: int = Query(20),
) -> JSONResponse:
  results = search_candidates(lat, lon, radius_miles, min_acres, min_bldg_sqft, min_score)
  return JSONResponse({"results": results})


@app.get("/api/candidate/{candidate_id}")
async def candidate(candidate_id: int) -> JSONResponse:
  conn = db_connection()
  try:
    row = conn.execute("SELECT * FROM candidates WHERE id = ?", (candidate_id,)).fetchone()
  finally:
    conn.close()

  if not row:
    raise HTTPException(status_code=404, detail="Candidate not found")

  return JSONResponse(
    {
      "candidate": dict(row),
      "signals": candidate_signals(candidate_id),
      "score": candidate_score(candidate_id),
    }
  )


def start_if_empty() -> None:
  init_storage()
  conn = db_connection()
  try:
    row = conn.execute("SELECT COUNT(*) AS count FROM candidates").fetchone()
    if row and row["count"] == 0:
      refresh_job(min_acres=10, min_bldg_sqft=50000)
  finally:
    conn.close()


if __name__ == "__main__":
  start_if_empty()
  import uvicorn

  uvicorn.run(app, host="127.0.0.1", port=8000)
