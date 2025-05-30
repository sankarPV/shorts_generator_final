# generate_short.py

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
ASPECT_RATIO = config["aspect_ratio"]

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

def generate_script_and_prompt(title):
    story_prompt = (
        f"Write a short, 30–60 second story script for kids featuring two consistent characters:\n"
        f"- Jay: A curious boy with slightly messy brown hair and bright inquisitive blue eyes, wearing a green shirt and brown pants.\n"
        f"- Tiger: A playful baby tiger with soft orange and black-striped fur.\n"
        f"The setting is a lush forest with tall trees, colorful flowers, and a gentle river.\n"
        f"Title: {title}.\n"
        f"The story should have a simple moral. Avoid changing their appearance, age, or personality."
    )

    image_prompt = (
        "Pixar-style image of a curious boy named Jay with slightly messy brown hair and bright inquisitive blue eyes, "
        "wearing a green shirt and brown pants, standing beside a playful baby tiger with soft orange and black-striped fur. "
        "They are in a lush green forest with tall trees, colorful flowers, and a gentle river."
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": story_prompt}]
    )
    script = response.choices[0].message.content.strip()
    return script, image_prompt

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

    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice=VOICE,
        input=text
    ) as response:
        audio_data = response.read()  # ✅ Correct usage
        with open(audio_path, "wb") as out:
            out.write(audio_data)


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

def main():
    ep_num = get_next_episode_number()
    title = generate_title()

    sanitized_title = title.replace('"', '').replace("'", '').replace(' ', '-')
    folder_name = f"ep{ep_num:02d}-{sanitized_title}"

    folder = OUTPUT_DIR / folder_name
    folder.mkdir(parents=True, exist_ok=True)

    script_path = folder / "script.txt"
    prompt_path = folder / "prompt.txt"

    if not script_path.exists() or not prompt_path.exists():
        script, img_prompt = generate_script_and_prompt(title)
        script_path.write_text(script)
        prompt_path.write_text(img_prompt)
    else:
        script = script_path.read_text()
        img_prompt = prompt_path.read_text()

    voice_path = folder / "voice.mp3"
    generate_voice(script_path, voice_path)

    image_path = folder / "image.jpg"
    generate_image(img_prompt, image_path)

    video_path = folder / "video.mp4"
    create_video(image_path, voice_path, video_path)

    print(f"✅ Completed: {folder_name}")

if __name__ == "__main__":
    main()

def generate_short():
    try:
        main()
        return "✅ Short generated successfully."
    except Exception as e:
        return f"❌ Error: {str(e)}"
