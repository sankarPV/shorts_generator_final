# repair_shorts.py

import os
import json
import subprocess
from pathlib import Path
from openai import OpenAI
from PIL import Image
import requests

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

client = OpenAI(api_key=config["openai_api_key"])
VOICE = config["voice"]
OUTPUT_DIR = Path(config["output_dir"])


def generate_image(prompt, image_path):
    if image_path.exists():
        print("🖼️ Image already exists. Skipping generation.")
        return
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    image_url = response.data[0].url
    img_data = requests.get(image_url).content
    with open(image_path, 'wb') as handler:
        handler.write(img_data)


def generate_voice(script_path, audio_path):
    if audio_path.exists():
        print("🎙️ Voice already exists. Skipping generation.")
        return
    with open(script_path, 'r') as f:
        text = f.read()
    response = client.audio.speech.create(
        model="tts-1",
        voice=VOICE,
        input=text
    )
    response.stream_to_file(audio_path)


def create_video(image_path, audio_path, video_path):
    if video_path.exists():
        print("🎬 Video already exists. Skipping rendering.")
        return
    cmd = [
        "ffmpeg",
        "-loop", "1",
        "-i", str(image_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-t", "60",
        "-y",
        str(video_path)
    ]
    subprocess.run(cmd, check=True)


def repair_episodes():
    for folder in sorted(OUTPUT_DIR.glob("ep*")):
        if not folder.is_dir():
            continue

        print(f"\n🔍 Checking {folder.name}")
        script_path = folder / "script.txt"
        prompt_path = folder / "prompt.txt"
        voice_path = folder / "voice.mp3"
        image_path = folder / "image.jpg"
        video_path = folder / "video.mp4"

        if not script_path.exists() or not prompt_path.exists():
            print("❌ Missing script or prompt. Skipping episode.")
            continue

        generate_voice(script_path, voice_path)
        generate_image(prompt_path.read_text(), image_path)
        create_video(image_path, voice_path, video_path)
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
