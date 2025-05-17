# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import asyncio
import os
import sys
import time
import json
import re
import numpy as np
import soundfile as sf
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

from rtclient import (
    InputTextContentPart,
    RTAudioContent,
    RTClient,
    RTFunctionCallItem,
    RTMessageItem,
    RTResponse,
    NoTurnDetection,
    UserMessageItem,
)
load_dotenv()

start_time = time.time()

INSTRUCTIONS="""
Read the children's story with lively, expressive emotions, creating an engaging, fun, and captivating experience for young listeners.

Guidelines:
## Expressive Emotions: Use a variety of vocal tones to match the emotions of each part of the story:
- Excitement: Increase energy, speak with a lively and slightly faster pace.
- Curiosity: Add a sense of wonder, using a slower, softer tone as if discovering something new.
- Suspense or Mystery: Lower your voice slightly, add pauses for anticipation, and speak more slowly.
- Joy and Happiness: Speak in a bright, cheerful tone, emphasizing positive words.

## Character Voices:
- Distinct voices for each character, even subtle shifts, help children differentiate between characters.
- Friendly Characters: Use a warm, gentle voice.
- Villains or Challenging Characters: Use a deeper or exaggerated tone that’s engaging but not overly frightening.
- Small or Cute Creatures: Consider a lighter, higher-pitched voice to add a sense of playfulness.

## Pacing and Pauses:
- Adjust the reading pace based on the story’s action. Read faster in exciting scenes and slower in suspenseful moments.
- Use pauses effectively to create suspense or emphasize important moments, giving children time to imagine the scene.
- After questions, pause briefly to give children a moment to reflect or wonder.

## Emphasis on Key Words and Phrases:
- Emphasize key words to enhance understanding and engagement. For instance, highlight words like "huge," "amazing," "whispered," "shouted," etc.
- Slightly stretch and stress words related to the setting, like “dark forest” or “bright, shining star,” to paint a more vivid picture.

## Natural Flow:
- Maintain a friendly, conversational tone overall. Avoid sounding robotic; instead, speak as if you’re telling the story directly to a group of curious children.
- Avoid rushing through sentences or lines; let each sentence land with its intended effect.

## Opening and title:
- For the opening and title, you should speak in a friendly and engaging tone, as if you're welcoming the children to the story.
- For the title, just read the title out. Don't add anything else.

## Important:
- You task is to read the EXACT story provided to you by the user. Don't add or change anything to it.
- If the text is non-verbal, just ignore it.
- Remember, your task is to read the text, not to generate it. For any user provided text, just read it out.
"""

def log(*args):
    elapsed_time_ms = int((time.time() - start_time) * 1000)
    print(f"{elapsed_time_ms} [ms]: ", *args)

async def receive_message_item(item: RTMessageItem, out_dir: str, fname: str):
    prefix = f"[response={item.response_id}][item={item.id}]"
    async for contentPart in item:
        if contentPart.type == "audio":

            async def collect_audio(audioContentPart: RTAudioContent):
                audio_data = bytearray()
                async for chunk in audioContentPart.audio_chunks():
                    audio_data.extend(chunk)
                return audio_data

            async def collect_transcript(audioContentPart: RTAudioContent):
                audio_transcript: str = ""
                async for chunk in audioContentPart.transcript_chunks():
                    audio_transcript += chunk
                return audio_transcript

            audio_task = asyncio.create_task(collect_audio(contentPart))
            transcript_task = asyncio.create_task(collect_transcript(contentPart))
            audio_data, audio_transcript = await asyncio.gather(audio_task, transcript_task)
            print(prefix, f"Audio received with length: {len(audio_data)}")
            print(prefix, f"Audio Transcript: {audio_transcript}")
            with open(os.path.join(out_dir, f"{fname}.wav"), "wb") as out:
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                sf.write(out, audio_array, samplerate=24000)
            with open(
                os.path.join(out_dir, f"{fname}.audio_transcript.txt"),
                "w",
                encoding="utf-8",
            ) as out:
                out.write(audio_transcript)
        elif contentPart.type == "text":
            text_data = ""
            async for chunk in contentPart.text_chunks():
                text_data += chunk
            print(prefix, f"Text: {text_data}")
            with open(os.path.join(out_dir, f"{fname}.text.txt"), "w", encoding="utf-8") as out:
                out.write(text_data)


async def receive_function_call_item(item: RTFunctionCallItem, out_dir: str, fname: str):
    prefix = f"[function_call_item={item.id}]"
    await item
    print(prefix, f"Function call arguments: {item.arguments}")
    with open(os.path.join(out_dir, f"{fname}.function_call.json"), "w", encoding="utf-8") as out:
        out.write(item.arguments)


async def receive_response(client: RTClient, response: RTResponse, out_dir: str, fname: str):
    prefix = f"[response={response.id}]"
    async for item in response:
        print(prefix, f"Received item {item.id}")
        if item.type == "message":
            asyncio.create_task(receive_message_item(item, out_dir, fname))
        elif item.type == "function_call":
            asyncio.create_task(receive_function_call_item(item, out_dir, fname))

    print(prefix, f"Response completed ({response.status})")


async def run(client: RTClient, out_dir: str, story: list[str]):
    user_messages = story

    log("Configuring Session...")
    await client.configure(
        instructions=INSTRUCTIONS,
        turn_detection=NoTurnDetection(),
        voice="alloy",
    )
    log("Done")
    for i, user_message in enumerate(user_messages):
        msg = f"Read out the following text: {user_message}"
        log(f"Sending User Message: {msg}")
        await client.send_item(UserMessageItem(content=[InputTextContentPart(text=msg)]))
        log("Done")
        response = await client.generate_response()
        fname = f"{i}"
        await receive_response(client, response, out_dir, fname)


def get_env_var(var_name: str) -> str:
    value = os.environ.get(var_name)
    if not value:
        raise OSError(f"Environment variable '{var_name}' is not set or is empty.")
    return value


async def with_azure_openai(out_dir: str, story: list[str]):
    endpoint = get_env_var("REALTIME_AZURE_OPENAI_ENDPOINT")
    key = get_env_var("REALTIME_AZURE_OPENAI_API_KEY")
    deployment = get_env_var("REALTIME_AZURE_OPENAI_DEPLOYMENT")
    os.makedirs(out_dir, exist_ok=True)
    async with RTClient(url=endpoint, key_credential=AzureKeyCredential(key), azure_deployment=deployment) as client:
        await run(client, out_dir, story)

    await client.close()

async def with_openai(out_dir: str, story: list[str]):
    key = get_env_var("OPENAI_API_KEY")
    model = get_env_var("OPENAI_MODEL")
    os.makedirs(out_dir, exist_ok=True)
    async with RTClient(key_credential=AzureKeyCredential(key), model=model) as client:
        await run(client, out_dir, story)
    await client.close()



if __name__ == "__main__":
    # Load the parsed SFX output
    with open("out/alice/parsed_sfx_output.json", "r", encoding='utf-8') as f:
        sfx_data = json.load(f)
    
    text_segments = sfx_data["text_segments"]
    
    # Run the text-to-speech generation
    asyncio.run(with_azure_openai("out/alice", text_segments))
