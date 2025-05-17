import argparse
from fab_audio.sfx import Sfx
import json
import os
from fab_audio.sfx import parse_sfx_output, all_audio_files
# from fab_audio.realtime_tts import with_azure_openai
from fab_audio.azure_oai import generate_story_audio
from fab_audio.mix_audio import mix_audio
import asyncio

def generate_audio(title: str, story: str, out_dir: str = None):
    if out_dir is None:
        out_dir = f"out/{title.lower().replace(' ', '_')}"
    os.makedirs(out_dir, exist_ok=True)

    # Generate the sfx
    if not os.path.exists(f"{out_dir}/sfx_output.json"):
        sfx = Sfx()
        sfx_dict = sfx.generate(title, story, out_dir)

    else:
        with open(f"{out_dir}/sfx_output.json", "r") as f:
            sfx_dict = json.load(f)

    # Parse the sfx
    if not os.path.exists(f"{out_dir}/parsed_sfx_output.json"):
        parsed_sfx_dict = parse_sfx_output(sfx_dict, out_dir, all_audio_files)
    else:
        with open(f"{out_dir}/parsed_sfx_output.json", "r") as f:
            parsed_sfx_dict = json.load(f)

    # Generate the audio
    text_segments = parsed_sfx_dict["text_segments"]
    # asyncio.run(with_azure_openai(out_dir, text_segments))
    generate_story_audio(text_segments, out_dir, title)

    # Mix the audio
    if not os.path.exists(f"{out_dir}/mixed.mp3"):
        mixed_path = mix_audio(parsed_sfx_dict, f"{out_dir}/mixed.mp3")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--language", type=str, default="en", help="The language to generate the stories in")
    arg_parser.add_argument("--n", type=int, default=1000, help="The number of stories to generate")
    arg_parser.add_argument("--story_path", type=str, default="generated_stories", help="The path to the generated stories")

    args = arg_parser.parse_args()

    story_path = args.story_path
    languages = ["en", "zh", "fr", "de"]
    language_indxe = { language: idx for idx, language in enumerate(languages)}

    if args.language not in languages:
        print(f"Language {args.language} not supported.")
        print(f"Supported languages: {languages}")
        exit(1)
    
    print(f"Generating {args.n} stories in {args.language}")

    selected_language_idx = language_indxe[args.language]
    n = 0
    for json_file in os.listdir(story_path):
        if not json_file.endswith(".json"):
            continue
        with open(f"{story_path}/{json_file}", "r") as f:
            stories = json.load(f)
            for story in stories:
                if n >= args.n:
                    break
                try:
                    title = story["title"]
                    # only generate the English language for now
                    language = story["translations"][selected_language_idx]["language"]
                    story_text = story["translations"][selected_language_idx]["text"]
                    out_dir = f"out/audios/{title.lower().replace(' ', '_')}_{language.lower()}"
                    print(f"Generating audio for {title} in {language}")
                    generate_audio(title, story_text, out_dir)
                    n += 1
                except Exception as e:
                    print(f"Error generating audio for {title} in {language}: {e}")

