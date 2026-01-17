import socket
import sqlite3
import sys
import threading
import time
import webbrowser
from dataclasses import asdict, dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

HTML_PAGE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>P3 Recon</title>
    <link
      rel="stylesheet"
      href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
      crossorigin=""
    />
    <style>
      :root {
        color-scheme: dark;
        font-family: "Share Tech Mono", "Fira Mono", ui-monospace, SFMono-Regular, Menlo,
          Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        background: #030712;
        color: #e2e8f0;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
      }

      #app {
        display: grid;
        grid-template-columns: minmax(280px, 360px) 1fr;
        height: 100vh;
        background: radial-gradient(circle at top, #0f172a, #020617 70%);
      }

      .panel {
        display: flex;
        flex-direction: column;
        gap: 16px;
        padding: 20px 22px;
        background: rgba(2, 6, 23, 0.92);
        border-right: 1px solid rgba(56, 189, 248, 0.2);
        backdrop-filter: blur(16px);
      }

      .title {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .pulse {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #38bdf8;
        box-shadow: 0 0 14px rgba(56, 189, 248, 0.9);
        animation: pulse 1.6s infinite;
      }

      h1 {
        margin: 0;
        font-size: 1.1rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
      }

      .subtitle {
        margin: 0;
        font-size: 0.8rem;
        color: rgba(226, 232, 240, 0.6);
      }

      label {
        font-size: 0.75rem;
        color: rgba(226, 232, 240, 0.65);
        display: grid;
        gap: 8px;
      }

      input,
      button {
        font-family: inherit;
      }

      input[type="text"] {
        padding: 10px 12px;
        border-radius: 10px;
        border: 1px solid rgba(56, 189, 248, 0.2);
        background: rgba(15, 23, 42, 0.6);
        color: #e2e8f0;
      }

      input[type="range"] {
        width: 100%;
        accent-color: #38bdf8;
      }

      button {
        padding: 10px 14px;
        border: 1px solid rgba(56, 189, 248, 0.5);
        border-radius: 10px;
        background: rgba(14, 116, 144, 0.35);
        color: #e2e8f0;
        font-weight: 600;
        cursor: pointer;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }

      button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 30px rgba(14, 116, 144, 0.35);
      }

      .status {
        padding: 10px 12px;
        border-radius: 10px;
        border: 1px solid rgba(56, 189, 248, 0.2);
        background: rgba(15, 23, 42, 0.6);
        font-size: 0.75rem;
        color: rgba(226, 232, 240, 0.7);
      }

      .results {
        display: grid;
        gap: 10px;
        overflow-y: auto;
      }

      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.75rem;
      }

      th,
      td {
        padding: 8px 6px;
        text-align: left;
        border-bottom: 1px solid rgba(56, 189, 248, 0.1);
      }

      th {
        color: rgba(226, 232, 240, 0.7);
        text-transform: uppercase;
        letter-spacing: 0.08em;
      }

      #map {
        height: 100%;
        width: 100%;
      }

      .leaflet-popup-content-wrapper {
        background: rgba(2, 6, 23, 0.95);
        color: #e2e8f0;
      }

      @keyframes pulse {
        0% {
          transform: scale(1);
        }
        50% {
          transform: scale(1.2);
        }
        100% {
          transform: scale(1);
        }
      }

      @media (max-width: 900px) {
        #app {
          grid-template-columns: 1fr;
        }

        .panel {
          position: absolute;
          z-index: 900;
          width: min(360px, 92vw);
          height: 100%;
        }
      }
    </style>
  </head>
  <body>
    <div id="app">
      <section class="panel">
        <div class="title">
          <span class="pulse"></span>
          <div>
            <h1>P3 Recon</h1>
            <p class="subtitle">Signal fusion console for P3 candidates.</p>
          </div>
        </div>

        <label>
          Location
          <input id="location" type="text" placeholder="Enter city or address" />
        </label>

        <label>
          Search radius: <span id="radius-value">15</span> mi
          <input id="radius" type="range" min="5" max="100" value="15" />
        </label>

        <button id="scan">Scan</button>

        <div class="status" id="status">Awaiting scan...</div>

        <div class="results">
          <table>
            <thead>
              <tr>
                <th>Lead</th>
                <th>Score</th>
              </tr>
            </thead>
            <tbody id="results"></tbody>
          </table>
        </div>
      </section>

      <div id="map"></div>
    </div>

    <script
      src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
      integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
      crossorigin=""
    ></script>
    <script>
      const map = L.map("map", { zoomControl: false }).setView([39.1, -94.58], 11);
      L.control.zoom({ position: "topright" }).addTo(map);
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: "&copy; OpenStreetMap contributors"
      }).addTo(map);

      const markerLayer = L.layerGroup().addTo(map);
      const radiusEl = document.getElementById("radius");
      const radiusValueEl = document.getElementById("radius-value");
      const resultsEl = document.getElementById("results");
      const statusEl = document.getElementById("status");

      radiusEl.addEventListener("input", () => {
        radiusValueEl.textContent = radiusEl.value;
      });

      async function geocode(query) {
        const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
          query
        )}`;
        const response = await fetch(url, {
          headers: { Accept: "application/json" }
        });
        if (!response.ok) {
          throw new Error("Geocoding failed");
        }
        const data = await response.json();
        if (!data.length) {
          throw new Error("No results");
        }
        return {
          lat: Number(data[0].lat),
          lon: Number(data[0].lon),
          display: data[0].display_name
        };
      }

      function renderResults(results) {
        resultsEl.innerHTML = "";
        results.forEach((lead) => {
          const row = document.createElement("tr");
          row.innerHTML = `<td>${lead.title}</td><td>${lead.score}</td>`;
          resultsEl.appendChild(row);
        });
      }

      async function runScan() {
        const locationInput = document.getElementById("location");
        const query = locationInput.value.trim();
        if (!query) {
          locationInput.focus();
          return;
        }

        statusEl.textContent = "Geocoding location...";
        resultsEl.innerHTML = "";
        markerLayer.clearLayers();

        try {
          const geo = await geocode(query);
          statusEl.textContent = `Scanning near ${geo.display}`;
          map.flyTo([geo.lat, geo.lon], 12, { duration: 1.2 });
          const radius = Number(radiusEl.value);
          const response = await fetch("/api/scan", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lat: geo.lat, lon: geo.lon, radius })
          });
          if (!response.ok) {
            throw new Error("Scan failed");
          }
          const data = await response.json();
          renderResults(data.results);
          statusEl.textContent = `Scan complete: ${data.results.length} leads.`;

          data.results.forEach((lead) => {
            const marker = L.circleMarker([lead.lat, lead.lon], {
              radius: 8,
              color: "#38bdf8",
              fillColor: "#38bdf8",
              fillOpacity: 0.85
            });
            marker.bindPopup(`<strong>${lead.title}</strong><br/>Score ${lead.score}`);
            marker.addTo(markerLayer);
          });
        } catch (error) {
          statusEl.textContent = `Scan failed: ${error.message}`;
        }
      }

      document.getElementById("scan").addEventListener("click", runScan);
      document.getElementById("location").addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          runScan();
        }
      });
    </script>
  </body>
</html>
"""


@dataclass
class Lead:
  title: str
  score: int
  lat: float
  lon: float


def get_app_data_dir() -> Path:
  if getattr(sys, "frozen", False):
    return Path(sys.executable).resolve().parent
  return Path(__file__).resolve().parent


def get_db_path() -> Path:
  return get_app_data_dir() / "p3_recon.db"


def init_db() -> None:
  conn = sqlite3.connect(get_db_path())
  try:
    conn.execute(
      """
      CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        score INTEGER NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
      )
      """
    )
    conn.commit()
  finally:
    conn.close()


def write_sample_leads(lat: float, lon: float) -> list[Lead]:
  leads = [
    Lead("Rivergate Freight Terminal", 92, lat + 0.02, lon - 0.01),
    Lead("Oak Ridge Transit Hub", 84, lat - 0.015, lon + 0.018),
    Lead("Cedar Point Industrial Park", 78, lat + 0.01, lon + 0.022),
  ]
  conn = sqlite3.connect(get_db_path())
  try:
    conn.execute("DELETE FROM leads")
    conn.executemany(
      "INSERT INTO leads (title, score, lat, lon) VALUES (?, ?, ?, ?)",
      [(lead.title, lead.score, lead.lat, lead.lon) for lead in leads],
    )
    conn.commit()
  finally:
    conn.close()
  return leads


def read_leads() -> list[Lead]:
  conn = sqlite3.connect(get_db_path())
  try:
    rows = conn.execute(
      "SELECT title, score, lat, lon FROM leads ORDER BY score DESC"
    ).fetchall()
    return [Lead(title=row[0], score=row[1], lat=row[2], lon=row[3]) for row in rows]
  finally:
    conn.close()


def get_free_port() -> int:
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind(("127.0.0.1", 0))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return sock.getsockname()[1]


def create_app() -> FastAPI:
  app = FastAPI(title="P3 Recon")
  app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
  )

  @app.get("/")
  async def root() -> HTMLResponse:
    return HTMLResponse(HTML_PAGE)

  @app.get("/api/leads")
  async def get_leads() -> JSONResponse:
    leads = [asdict(lead) for lead in read_leads()]
    return JSONResponse({"results": leads})

  @app.post("/api/scan")
  async def scan(payload: dict) -> JSONResponse:
    lat = float(payload.get("lat", 0))
    lon = float(payload.get("lon", 0))
    write_sample_leads(lat, lon)
    leads = [asdict(lead) for lead in read_leads()]
    return JSONResponse({"results": leads})

  return app


def open_browser(url: str) -> None:
  time.sleep(1.0)
  webbrowser.open(url)


def run() -> None:
  init_db()
  port = get_free_port()
  url = f"http://127.0.0.1:{port}"
  app = create_app()

  server = uvicorn.Server(
    uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
  )

  browser_thread = threading.Thread(target=open_browser, args=(url,), daemon=True)
  browser_thread.start()

  server.run()


if __name__ == "__main__":
  run()
