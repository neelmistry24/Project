from __future__ import annotations

from fastapi import FastAPI

from config import ensure_directories, load_config
from database import ActivityDatabase
from monitor import Monitor
from reports import recent_dataframe, summary_metrics


config = load_config()
ensure_directories(config)
db = ActivityDatabase(config.database_path)
app = FastAPI(title="Employee Screen Activity Recognition API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/logs")
def logs(limit: int = 100) -> dict[str, list[dict[str, object]]]:
    df = recent_dataframe(db, limit=limit)
    if "captured_at" in df.columns:
        df["captured_at"] = df["captured_at"].astype(str)
    return {"logs": df.fillna("").to_dict(orient="records")}


@app.get("/summary")
def summary(limit: int = 500) -> dict[str, float]:
    df = recent_dataframe(db, limit=limit)
    return summary_metrics(df)


@app.post("/settings/monitoring")
def set_monitoring(enabled: bool) -> dict[str, bool]:
    db.set_setting("monitoring_enabled", enabled)
    return {"monitoring_enabled": db.monitoring_enabled()}


@app.post("/capture")
def capture_now() -> dict[str, int | str]:
    event_id = Monitor().capture_once()
    if event_id is None:
        return {"status": "paused"}
    return {"status": "captured", "event_id": event_id}
