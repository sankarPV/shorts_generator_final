# upload_to_youtube.py

import os
import pickle
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime, timedelta, timezone

# YouTube API setup
SCOPES = SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]
CLIENT_SECRET_FILE = "client_secret.json"
CREDENTIALS_FILE = "youtube_token.pickle"
OUTPUT_DIR = Path("output")
CONFIG_FILE = "upload_config.json"
UPLOADED_LOG_FILE = "uploaded_videos.json"

# Load configuration
with open(CONFIG_FILE, "r") as f:
    config_data = json.load(f)

EXPECTED_CHANNEL_NAME = config_data.get("expected_channel_name", "Jay & Tiger Shorts")
DEFAULT_DESCRIPTION = config_data.get("default_description", "A short story from Jay & Tiger!")
DEFAULT_TAGS = config_data.get("tags", ["shorts", "kids", "story", "jayandtiger"])
CATEGORY_ID = config_data.get("category_id", "1")
PRIVACY_STATUS = config_data.get("privacy_status", "unlisted")

# Load uploaded video log
if os.path.exists(UPLOADED_LOG_FILE):
    with open(UPLOADED_LOG_FILE, "r") as f:
        uploaded_videos = json.load(f)
else:
    uploaded_videos = {}

# Authenticate and return YouTube service
def get_authenticated_service():
    creds = None
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(CREDENTIALS_FILE, "wb") as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)

# Check the authenticated channel name
def check_channel_name(youtube):
    response = youtube.channels().list(part="snippet", mine=True).execute()
    if response["items"]:
        actual_name = response["items"][0]["snippet"]["title"]
        if actual_name != EXPECTED_CHANNEL_NAME:
            print(f"❌ You're logged into '{actual_name}', but expected '{EXPECTED_CHANNEL_NAME}'.")
            print("🔁 Delete youtube_token.pickle and re-run the script to choose the correct channel.")
            exit(1)
        else:
            print(f"✅ Authenticated as: {actual_name}")
    else:
        print("❌ Could not verify your YouTube channel.")
        exit(1)

# Extract episode number and title
def parse_title(folder_name):
    parts = folder_name.split("-", 1)
    ep_num = parts[0][2:]  # Extract 01 from ep01
    title = parts[1].replace("-", " ").title()
    return f"Jay & Tiger: Episode {int(ep_num)}: {title}"

# Get scheduled time - 6 PM IST
def get_scheduled_time():
    # Schedule for next 6 PM IST (UTC+5:30)
    now_utc = datetime.now(timezone.utc)
    today_6pm_ist = now_utc.astimezone().replace(hour=18, minute=0, second=0, microsecond=0)
    scheduled_time = today_6pm_ist - timedelta(hours=5, minutes=30)  # convert IST to UTC
    if now_utc >= scheduled_time:
        scheduled_time += timedelta(days=1)
    return scheduled_time.isoformat()

# Upload video
def upload_video(youtube, folder):
    video_path = folder / "video.mp4"
    if not video_path.exists():
        print(f"❌ Video not found in {folder.name}, skipping.")
        return

    if folder.name in uploaded_videos:
        print(f"⏩ Already uploaded: {folder.name}, skipping.")
        return

    title = parse_title(folder.name)
    description = (folder / "script.txt").read_text() if (folder / "script.txt").exists() else DEFAULT_DESCRIPTION

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": DEFAULT_TAGS,
            "categoryId": CATEGORY_ID
        },
        "status": {
            "privacyStatus": PRIVACY_STATUS,
            "publishAt": get_scheduled_time()
        }
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/*")
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    response = request.execute()

    print(f"✅ Uploaded: {title} → https://youtu.be/{response['id']}")

    # Record uploaded video
    uploaded_videos[folder.name] = response['id']
    with open(UPLOADED_LOG_FILE, "w") as f:
        json.dump(uploaded_videos, f, indent=2)

# Main runner
def main():
    youtube = get_authenticated_service()
    check_channel_name(youtube)

    for folder in sorted(OUTPUT_DIR.glob("ep*")):
        if folder.is_dir():
            upload_video(youtube, folder)

# Allow command-line execution
if __name__ == "__main__":
    main()

def upload_to_youtube():
    try:
        main()
        return "✅ Short uploaded successfully."
    except Exception as e:
        return f"❌ Error: {str(e)}"