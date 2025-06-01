import os
import json
import subprocess
from pathlib import Path
from openai import OpenAI
import wave
import contextlib
import random

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

client = OpenAI(api_key=config["openai_api_key"])
VOICE = config["voice"]
OUTPUT_DIR = Path(config["output_dir"])
VIDEO_CLIPS_DIR = Path("assets/video")

def generate_voice(script_path, audio_path):
    if audio_path.exists():
        print("🎙️ Voice already exists. Skipping generation.")
        return
    with open(script_path, 'r') as f:
        text = f.read()
    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice=VOICE,
        input=text
    ) as response:
        audio_data = response.read()
        with open(audio_path, "wb") as out:
            out.write(audio_data)

def get_audio_duration(audio_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())

def create_video_from_clips(clip_paths, audio_path, output_path):
    if output_path.exists():
        print("🎬 Video already exists. Skipping rendering.")
        return

    audio_duration = get_audio_duration(audio_path)
    temp_list = "temp_list.txt"
    looped_clips = []

    current_duration = 0
    while current_duration < audio_duration:
        clip = random.choice(clip_paths)
        looped_clips.append(f"file '{clip.resolve()}'\n")
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(clip)],
            capture_output=True, text=True
        )
        current_duration += float(result.stdout.strip())

    with open(temp_list, "w") as f:
        f.writelines(looped_clips)

    merged_video = output_path.with_name("temp_merged.mp4")
    subprocess.run(["ffmpeg", "-f", "concat", "-safe", "0", "-i", temp_list, "-c", "copy", str(merged_video)], check=True)
    os.remove(temp_list)

    cmd = [
        "ffmpeg", "-i", str(merged_video), "-i", str(audio_path),
        "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-y", str(output_path)
    ]
    subprocess.run(cmd, check=True)
    os.remove(merged_video)

def repair_episodes():
    available_clips = sorted([f for f in VIDEO_CLIPS_DIR.glob("*.mp4")])

    for folder in sorted(OUTPUT_DIR.glob("ep*")):
        if not folder.is_dir():
            continue

        print(f"\n🔍 Checking {folder.name}")
        script_path = folder / "script.txt"
        voice_path = folder / "voice.mp3"
        video_path = folder / "video.mp4"

        if not script_path.exists():
            print("❌ Missing script. Skipping episode.")
            continue

        generate_voice(script_path, voice_path)
        create_video_from_clips(available_clips, voice_path, video_path)
        print(f"✅ Repaired: {folder.name}")

# Main runner
def main():
    repair_episodes()

# Allow command-line execution
if __name__ == "__main__":
    main()

def repair_shorts():
    try:
        main()
        return "✅ Short repaired successfully."
    except Exception as e:
        return f"❌ Error: {str(e)}"
