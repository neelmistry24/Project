from pathlib import Path
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "screenshots")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_screenshot(local_path: str, category: str) -> tuple[str, str]:
    file_path = Path(local_path)
    cloud_path = f"employee_screenshots/{category}/{file_path.name}"

    with open(file_path, "rb") as file:
        supabase.storage.from_(SUPABASE_BUCKET).upload(
            path=cloud_path,
            file=file,
            file_options={
                "content-type": "image/png",
                "upsert": "true",
            },
        )

    public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(cloud_path)
    return public_url, cloud_path


def delete_screenshots(cloud_paths: list[str]) -> None:
    if cloud_paths:
        supabase.storage.from_(SUPABASE_BUCKET).remove(cloud_paths)
    
def get_screenshot_url(cloud_path: str) -> str:
    return supabase.storage.from_(SUPABASE_BUCKET).get_public_url(cloud_path)