import os
import base64
import time
from pathlib import Path
from typing import List, Optional
import logging
from openai import APIError
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

client = AzureOpenAI(
    api_key=os.getenv("AUDIO_AZURE_OPENAI_API_KEY"),
    api_version="2025-02-01-preview",
    azure_endpoint=os.getenv("AUDIO_AZURE_OPENAI_ENDPOINT")
)
model = os.getenv("AUDIO_AZURE_OPENAI_DEPLOYMENT", "gpt-4o-audio-preview")
    
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
- Remember, your task is to read the text, not expand it. For any user provided text, just read it out.
"""

def generate_audio(
    text: str, 
    output_dir: str, 
    file_name: str,
    voice: str = "alloy",
    format: str = "mp3",
    max_retries: int = 3,
    retry_delay: int = 2
) -> Optional[str]:
    """
    Generate audio from text using Azure OpenAI's GPT-4o-audio model.
    
    Args:
        text: The text to convert to speech
        output_dir: Directory to save the audio file
        file_name: Name of the output file (without extension)
        voice: Voice to use (default: "alloy")
        format: Audio format (default: "mp3")
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        Path to the generated audio file or None if failed
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Full path for the output file
    full_file_path = output_path / f"{file_name}"
    
    
    for attempt in range(max_retries):
        logger.info(f"Generating audio for text: {text}...")
        
        err_msg = None
        try:
            if err_msg is None:
                user_msg = f"Read out the following text: {text}"
            else:
                user_msg = f"Previous error: {err_msg}. Just read out the following text: {text}"
            completion = client.chat.completions.create(
                model=model,
                modalities=["text", "audio"],
                audio={"voice": voice, "format": format},
                messages=[
                    {
                        "role": "system",
                        "content": INSTRUCTIONS
                    },
                    {
                        "role": "user",
                        "content": user_msg
                    }
                ]
            )
            

            text = completion.choices[0].message.content
            if text:
                print(text)
            
            # Decode the base64 audio data
            audio_bytes = base64.b64decode(completion.choices[0].message.audio.data)
            # Save the audio file
            with open(full_file_path, "wb") as f:
                f.write(audio_bytes)
            
            logger.info(f"Audio saved to {full_file_path}")
            return str(full_file_path)
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            err_msg = str(e)
    
    return None

def generate_story_audio(
    texts: List[str], 
    out_dir: str = None,
    story_name: str = None,
    voice: str = "alloy",
    format: str = "mp3"
) -> List[str]:
    """
    Generate audio files for a list of texts representing a story.
    
    Args:
        texts: List of text segments to convert to audio
        story_name: Name of the story (used for the output directory)
        voice: Voice to use for all segments
        format: Audio format for all segments
        
    Returns:
        List of paths to the generated audio files
    """
    if out_dir is None:
        out_dir = f"out/{story_name.lower().replace(' ', '_')}"
    os.makedirs(out_dir, exist_ok=True)

    generated_files = []
    
    for i, text in enumerate(texts):
        file_name = f"{i}.mp3"
        logger.info(f"Processing segment {i+1}/{len(texts)} for story '{story_name}'")
        
        if os.path.exists(f"{out_dir}/{file_name}"):
            logger.info(f"Skipping segment {i+1} because it already exists")
            generated_files.append(f"{out_dir}/{file_name}")
            continue
        
        file_path = generate_audio(
            text=text,
            output_dir=out_dir,
            file_name=file_name,
            voice=voice,
            format=format
        )
        
        if file_path:
            generated_files.append(file_path)
        else:
            logger.warning(f"Failed to generate audio for segment {i+1}")
    
    logger.info(f"Generated {len(generated_files)} audio files for story '{story_name}'")
    return generated_files

def main():
    """
    Test function to demonstrate the generate_audio functionality.
    """
    test_text = "Hello world! This is a test of the Azure OpenAI text-to-speech functionality. The quick brown fox jumps over the lazy dog."
    output_directory = "test_output"
    file_name = "test_audio"
    voice = "alloy"  # You can change this to other available voices like "nova", "echo", "fable", "onyx", "shimmer"
    
    logger.info("Starting test of generate_audio function")
    
    audio_path = generate_audio(
        text=test_text,
        output_dir=output_directory,
        file_name=file_name,
        voice=voice
    )
    
    if audio_path:
        logger.info(f"Test successful! Audio generated at: {audio_path}")
    else:
        logger.error("Test failed. No audio was generated.")

if __name__ == "__main__":
    main()
