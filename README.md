# P3 Spotter (FastAPI + Leaflet)

P3 Spotter is a **two-file** demo app you can run locally or package into a
single executable. It includes:

- `app.py` — FastAPI backend that serves the UI and a `/search` endpoint.
- `index.html` — single-file frontend with Leaflet map + Nominatim geocoding.

The backend serves `index.html` at `http://localhost:8000/`.

---

## What you need installed

### Required dependencies

- **Python 3.10+**
- **pip** (comes with Python)

### Python packages (installed via `requirements.txt`)

- `fastapi` — web framework
- `uvicorn` — ASGI server
- `pyinstaller` — optional, for building an executable

---

## Run locally (recommended)

### 1) Create and activate a virtual environment

**macOS / Linux**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\\Scripts\\Activate.ps1
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Start the app

```bash
python app.py
```

### 4) Open the UI

Visit: **http://localhost:8000**

---

## Use the app

1. Type a city or address into the **Location** field.
2. Adjust the **Search radius** slider.
3. Click **Find P3 leads** (or press **Enter**).
4. Results appear in the list and as map markers.
5. Click a marker to see the lead title + score.

---

## Build a desktop executable (optional)

`pyinstaller` can bundle the backend and `index.html` into one file.

### 1) Ensure dependencies are installed

```bash
pip install -r requirements.txt
```

### 2) Build the executable

**macOS / Linux**
```bash
pyinstaller --onefile --add-data "index.html:." app.py
```

**Windows (PowerShell)**
```powershell
pyinstaller --onefile --add-data "index.html;." app.py
```

### 3) Run the executable

The binary will be in the `dist/` folder.

```bash
./dist/app
```

Then open: **http://localhost:8000**

---

## Troubleshooting

### “ModuleNotFoundError: No module named 'fastapi'”
You skipped dependency installation. Run:

```bash
pip install -r requirements.txt
```

### “Permission denied” on Windows
Try PowerShell as admin or run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Port already in use
If port `8000` is busy, set a different one:

```bash
UVICORN_PORT=8010 python app.py
```

---

## File layout

```
app.py         # FastAPI backend + /search
index.html     # Leaflet UI
requirements.txt
README.md
```
