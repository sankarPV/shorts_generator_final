import os
import json
import subprocess
import random
from pathlib import Path
from openai import OpenAI
import wave
import contextlib

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

client = OpenAI(api_key=config["openai_api_key"])
VOICE = config["voice"]
OUTPUT_DIR = Path(config["output_dir"])
VIDEO_CLIPS_DIR = Path("assets/video")

def get_next_episode_number():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    episodes = [f.name for f in OUTPUT_DIR.iterdir() if f.is_dir() and f.name.startswith("ep")]
    if not episodes:
        return 1
    latest = max(int(e[2:].split("-")[0]) for e in episodes)
    return latest + 1

def generate_title():
    prompt = "Give me a short, creative episode title for a children's story about a boy named Jay and his baby tiger friend in a forest."
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip().replace(" ", "-").lower()

def generate_script(title):
    story_prompt = (
        f"Write a short, 30–60 second story script for kids featuring two consistent characters:\n"
        f"- Jay: A curious boy with slightly messy brown hair and bright inquisitive blue eyes, wearing a green shirt and brown pants.\n"
        f"- Tiger: A playful baby tiger with soft orange and black-striped fur.\n"
        f"The setting is a lush forest with tall trees, colorful flowers, and a gentle river.\n"
        f"Title: {title}.\n"
        f"The story should have a simple moral. Avoid changing their appearance, age, or personality."
    )
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": story_prompt}]
    )
    return response.choices[0].message.content.strip()

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

def main():
    ep_num = get_next_episode_number()
    title = generate_title()
    sanitized_title = title.replace('"', '').replace("'", '').replace(' ', '-')
    folder_name = f"ep{ep_num:02d}-{sanitized_title}"
    folder = OUTPUT_DIR / folder_name
    folder.mkdir(parents=True, exist_ok=True)

    script_path = folder / "script.txt"
    if not script_path.exists():
        script = generate_script(title)
        script_path.write_text(script)
    else:
        script = script_path.read_text()

    voice_path = folder / "voice.mp3"
    generate_voice(script_path, voice_path)

    available_clips = sorted([f for f in VIDEO_CLIPS_DIR.glob("*.mp4")])
    video_path = folder / "video.mp4"
    create_video_from_clips(available_clips, voice_path, video_path)

    print(f"✅ Completed: {folder_name}")

def generate_short():
    try:
        main()
        return "✅ Short generated successfully."
    except Exception as e:
        return f"❌ Error: {str(e)}"

if __name__ == "__main__":
    main()
