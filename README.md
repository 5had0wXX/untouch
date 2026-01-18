# Untouch P3 Finder (Connecticut)

A **beginner-friendly**, local-only P3 candidate finder for Connecticut.

**Run it with one command:**
```bash
python app.py
```

No Docker, no paid APIs, no frontend build step.

---

## ✅ What this app does

- Builds a **candidate universe** from Connecticut parcel data (commercial/industrial/institutional only).
- Enriches candidates with **public OSINT signals** (news, WARN notices, tax sale keywords).
- Produces an **explainable score** with evidence links.
- Provides a **sleek hacker-style UI** with map, filters, details drawer, and CSV export.

---

## ✅ Requirements

Install **Python 3.10+** (Windows):
- https://www.python.org/downloads/

---

## ✅ First-time setup (Windows)

Open **Command Prompt** in this folder and run:

```bat
pip install -r requirements.txt
python app.py
```

Then open:
```
http://127.0.0.1:8000
```

---

## ✅ First-run dataset behavior

On the **first refresh**, the backend tries to download a Connecticut parcel dataset automatically.
If it **cannot download**, it will fall back to a small built-in sample so the app still works.

### Preferred dataset (auto-download attempt)

The app tries to download from:
```
https://data.ct.gov/resource/5mzw-sjtu.csv
```

If this link changes or the download fails, you can **manually download** the CSV and save it as:
```
ct_parcels.csv
```
next to `app.py`.

---

## ✅ Run instructions (one command)

From the repo folder:

```bat
python app.py
```

---

## ✅ Usage

1. Enter a location (e.g. **Hartford, CT**).
2. Set your radius and minimum thresholds.
3. Click **Scan / Refresh**.
4. Results appear in the table and on the map.
5. Click any result for the **Why** panel with score + evidence.
6. Use **Download CSV** to export.

---

## ✅ What counts as a candidate

Only parcels with:
- **Commercial / Industrial / Institutional** land-use keywords
- **≥ 10 acres** (default)
- **≥ 50,000 sqft** building (default)

Residential, restaurant, retail, and small storefronts are filtered out.

---

## ✅ Data storage

A local SQLite file named **`untouch.db`** is created next to `app.py`.

---

## ✅ No paid APIs

All signals use free/public sources:
- Google News RSS
- CT WARN public listings
- Public tax sale / foreclosure keywords in news

Cached requests and polite rate limits are built-in.

---

## ✅ Troubleshooting

**1) `ModuleNotFoundError`**
```bat
pip install -r requirements.txt
```

**2) Port already in use**
Stop the other service or use:
```bat
python -m uvicorn app:app --port 8010
```

**3) No results**
Click **Scan / Refresh** first. Results only appear after a refresh.

---

## ✅ File layout

```
app.py         # FastAPI backend + CT data refresh
index.html     # UI
requirements.txt
untouch.db     # created at runtime
```
