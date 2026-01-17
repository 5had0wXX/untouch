# P3 Spotter (FastAPI + Leaflet)

This is a two-file demo app:
- `app.py` (FastAPI backend)
- `index.html` (self-contained frontend)

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: `http://localhost:8000`

## Build a desktop executable (Windows/macOS/Linux)

`pyinstaller` can package the FastAPI server and the HTML file into a single executable.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pyinstaller --onefile --add-data "index.html:." app.py
```

The executable will be created in the `dist/` directory. Run it and then open
`http://localhost:8000` in your browser.

> Note: On Windows, replace `:` with `;` in the `--add-data` argument:
> `--add-data "index.html;."`
