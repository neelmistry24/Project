# Employee Screen Activity Recognition Tool

This is a beginner-friendly AI/ML project based on the provided PDF requirement.

The project monitors screen activity, classifies it as `productive`, `non_productive`, or `idle`, stores the result locally, and shows everything on a redesigned ScreenSense dashboard.

## Simple Workflow

```text
Screen capture
    -> Active app + window title
    -> OCR text extraction
    -> Activity classifier
    -> SQLite database
    -> Streamlit dashboard
    -> Optional FastAPI backend
```

## What The Project Does

- Captures periodic screenshots.
- Detects active application and window title.
- Uses OCR if Tesseract is available.
- Classifies activity into:
  - `productive`
  - `non_productive`
  - `idle`
- Stores logs in SQLite.
- Shows a real-time Streamlit dashboard.
- Displays screenshots in three tabs:
  - Productive
  - Non-Productive
  - Idle
- Blurs non-productive screenshots before saving for privacy.
- Provides CSV report export.
- Provides a privacy/monitoring toggle.
- Includes FastAPI backend endpoints.
- Works locally and offline.

## Tech Stack From PDF

| Requirement | Used In Project |
| --- | --- |
| Client | Streamlit dashboard in `app.py` |
| Backend | FastAPI in `api.py` |
| Database | SQLite in `data/activity.db` |
| Image Processing | PIL, screenshot capture, image brightness check |
| OCR | `pytesseract` in `ocr_engine.py` |
| ML/CNN Extension | Classifier structure in `classifier.py` can be extended with CNN/Vision models |
| Reports | Charts, tables, CSV export in dashboard |
| Privacy | Monitoring toggle before capture |
| Screenshot Privacy | Non-productive screenshots are blurred before storage |

## Run The Project

Open PowerShell:

```powershell
cd "C:\Users\inspi\OneDrive\Documents\New project\EmployeeScreenActivityProject"
```

Install requirements:

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run dashboard:

```powershell
..\.venv\Scripts\python.exe -m streamlit run app.py
```

Open:

```text
http://localhost:8501
```

## Run Real Monitoring

Open a second PowerShell terminal:

```powershell
cd "C:\Users\inspi\OneDrive\Documents\New project\EmployeeScreenActivityProject"
..\.venv\Scripts\python.exe monitor.py
```

This captures screenshots repeatedly and saves results to SQLite.

## Run Backend API

Open a third PowerShell terminal:

```powershell
cd "C:\Users\inspi\OneDrive\Documents\New project\EmployeeScreenActivityProject"
..\.venv\Scripts\python.exe -m uvicorn api:app --reload
```

API URL:

```text
http://localhost:8000
```

Useful endpoints:

```text
/health
/logs
/summary
/capture
/settings/monitoring
```

The dashboard automatically connects to FastAPI when it is running. If FastAPI is not running, the dashboard uses SQLite directly.

## File Guide

```text
app.py          Streamlit frontend dashboard
api.py          FastAPI backend
monitor.py      Continuous screenshot monitoring
capture.py      Screenshot, active window, idle time
classifier.py   Productive / non-productive / idle logic
ocr_engine.py   OCR text extraction
database.py     SQLite table and insert/fetch functions
reports.py      Summary metrics and CSV export
config.yaml     Settings and keywords
seed_demo.py    Creates demo data and screenshots
```

## Classification Logic

The classifier checks:

```text
idle seconds
active app
window title
OCR text
screen brightness
keywords
```

Examples:

```text
VS Code, Python, Excel, GitHub -> productive
YouTube, Instagram, Netflix -> non_productive
Desktop, no active work, blank screen -> idle
```

## Privacy Features

```text
Monitoring can be turned ON/OFF
Data is stored locally
No keylogging
Non-productive screenshots are blurred before saving
Dashboard shows only latest 3 screenshots per category
```

## Demo Data

To create sample records and screenshots:

```powershell
..\.venv\Scripts\python.exe seed_demo.py
```

## Beginner Presentation Line

This project captures employee screen activity, extracts OCR and active-window information, classifies the activity into productive, non-productive, or idle, saves it into SQLite, and displays real-time reports and categorized screenshots on a Streamlit dashboard.
