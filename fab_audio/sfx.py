import re
from pydantic import BaseModel, Field
from typing import Dict
import json
import os
from openai import AzureOpenAI
# from langfuse.openai import AzureOpenAI
from dotenv import load_dotenv
# from langfuse.decorators import observe, langfuse_context



SFX_CANDIDATES_GENERATION_PROMPT = """
You are an expert in creating immersive audio-augmented storytelling for children. Your task is to generate a JSON dictionary for a given story, containing sound effects and background music, structured as follows:

## Structure

### 1. Sound Effects
- A dictionary where the key is the name of a sound effect (e.g., “hop”, “whistle”, “growl”) suitable for children’s storytelling.
- The value is a detailed dictionary containing:
  - **"keyword"**: Related words or phrases to help search for the sound.
  - **"description"**: A brief explanation of the sound’s action or source.
  - **"mode"**: Specifies how the sound should be mixed with the story audio, either:
    - **"overlay"**: The sound effect plays along with the audio.
    - **"exclusive"**: The sound effect temporarily pauses the story audio while it plays.

### 2. Text Augmentation
- The story text is augmented with **<sound_effect>** tags, placed where the sound effect should be heard. These tags should enhance the storytelling experience, without altering the original story’s tone or meaning.

### 3. Background Music
- A dictionary with:
  - **"keyword"**: Keywords to identify a suitable background track.
  - **"description"**: A brief explanation of the track’s tone or setting.

## Requirements
- Sound effects and background music should be simple, easy to imagine, and relatable for young readers.
- Add sound effects sparingly and at meaningful moments to enhance immersion without overwhelming the story.
- Ensure all JSON fields are properly formatted, and **<sound_effect>** tags are placed logically and naturally within the story.

## Example

### Input
The dog barked loudly and ran toward the gate.

### Output
```json
{
  "sound_effects": {
    "bark": {
      "keyword": ["bark", "dog"],
      "description": "sharp sound of a dog barking",
      "mode": "overlay"
    },
    "patter": {
      "keyword": ["patter", "paws"],
      "description": "light tapping sound of paws running on a hard surface",
      "mode": "exclusive"
    }
  },
  "text": "<bark> The dog barked loudly and ran toward the gate. <patter>",
  "bg_music": {
    "keyword": ["mysterious", "forest"],
    "description": "mysterious forest"
  }
}
"""

SFX_GENERATION_WITH_DATABASE_PROMPT = """
### SFX Generation with Database Prompt

You are an expert in designing immersive audio-augmented storytelling experiences for children. Your goal is to create a JSON dictionary for a given story, incorporating sound effects and background music to enhance the narrative. Follow the structured requirements below:

---

### **Output Structure**

#### 1. **Sound Effects**
- A dictionary where:
  - The key is the name of a sound effect (e.g., “hop”, “whistle”, “growl”) suitable for children’s storytelling.
  - The value is a dictionary containing:
    - "name": The name of the sound effect from the **SFX database**. Must match exactly with the names provided in the database.
    - "mode": Determines how the sound interacts with the story audio, with two options:
      - "overlay": The sound plays simultaneously with the story audio.
      - "exclusive": The sound pauses the story audio while it plays.

#### 2. **Text Augmentation**
- The story text is enriched with <sound_effect_name> tags, where the sound_effect_name is the name of the sound effect that in the sound effects dictionary generated as mentioned above.
  - Insert tags at appropriate moments where the sound effect should be heard.
  - Tags must enhance immersion while preserving the original tone and meaning of the story.
  - Remove unnecessary spaces, punctuation, and line breaks in the original text.

#### 3. **Background Music**
- A dictionary containing:
  - "name": The name of the background music from the **BGM database**, chosen to complement the story's mood and pacing.

---

#### SFX Database
(each sound effect is separated by a comma)
{all_sfx_names}

---

#### BGM Database
(each background music is separated by a comma)
{all_bgm_names}

---

### **Key Requirements**

1. **Sound Effect Integration:**
   - Select sound effects that align naturally with the events in the story.
   - Use sound effects sparingly and meaningfully to enhance the story.
   - Ensure the selected sound effect names strictly match those in the database.

2. **Text Tagging:**
   - Place <sound_effect_name> tags logically and unobtrusively within the story text.
   - Tags must reflect actions or events in the narrative that would benefit from auditory enhancement.

3. **Background Music:**
   - Choose music that complements the story’s theme and atmosphere.
   - Background music should be consistent with a child-friendly listening experience.

---

### **Example**

#### Input:
The dog barked loudly and ran toward the gate.

#### Output:
{{
  "sound_effects": {{
    "bark": {{
      "name": "bark",
      "mode": "overlay"
    }},
    "patter": {{
      "name": "patter",
      "mode": "exclusive"
    }}
  }},
  "text": "<bark> The dog barked loudly and ran toward the gate. <patter>",
  "bg_music": {{
    "name": "mysterious"
  }}
}}
"""

OPENING_GENERATION_PROMPT = """
# System Instruction: Create an Opening for the "Fablette" Children's Storytelling Podcast

You are an expert in crafting captivating openings for a children's storytelling podcast named **"Fablette"**. Your task is to generate a short, magical, and engaging introduction for each episode based on the provided story. The introduction should immediately invite listeners into the story being told.

## Structure of the Opening

1. **Welcome Line**:
   - Start with: "Welcome to Fablette, where stories come alive!"

2. **Story Teaser**:
   - Briefly introduce the story and its key theme or character. Include one or two sentences that excite the listeners about what’s to come.

3. **Call to Adventure**:
   - Conclude with an invitation to the story, such as, "Are you ready? Let’s begin!"

## Example Output

### For *Alice in Wonderland*
Welcome to Fablette, where stories come alive! Today, we’re telling the tale of Alice, a curious girl who tumbles into a magical world full of wonder and surprises. Are you ready? Let’s begin!

### For *The Three Little Pigs*
Welcome to Fablette, where stories come alive! Today’s story is about three clever pigs and a tricky wolf who huffs and puffs to blow their houses down. Are you ready? Let’s begin!

## Requirements
- Generate the PLAIN opening text from the given input story, without any extra explanations, commentary or quotation marks.
- Keep the opening concise (under 40–50 words).
- Use simple and engaging language that captures children’s imagination.
- Tailor the teaser to the specific theme of the story.
- Maintain a warm and magical tone throughout.
"""


all_sfx = {}
all_sfx_names = []
# read the database
for file in os.listdir("data/sfx"):
    fname = file.split(".")[0]
    all_sfx[fname] = str(os.path.join("data/sfx", file))
    all_sfx_names.append(fname)

all_sfx_names = ", ".join(all_sfx_names)

all_bgm_names = []
all_bgm = {}
for file in os.listdir("data/bg_music"):
    fname = file.split(".")[0]
    all_bgm[fname] = str(os.path.join("data/bg_music", file))
    all_bgm_names.append(fname)

all_bgm_names = ", ".join(all_bgm_names)

all_misc = {}
for file in os.listdir("data/misc"):
    fname = file.split(".")[0]
    all_misc[fname] = str(os.path.join("data/misc", file))

all_audio_files = {}
all_audio_files.update(all_sfx)
all_audio_files.update(all_bgm)
all_audio_files.update(all_misc)


TEST_STORY = """
One sunny day, Alice and her sister went out for a walk in the garden, and while her sister was busy reading a book, Alice got very bored. Suddenly, Alice spotted a white bunny that was in a hurry.
She was curious so she went after the bunny. The bunny fell through a big hole in a tree trunk, and Alice followed him. Suddenly Alice found herself falling into a very deep well. Then, she finally landed and saw a long corridor ahead of her.
"""

class SfxEffect(BaseModel):
    mode: str
    name: str | None = None
    keyword: list[str] | None = None
    description: str | None = None

class BgMusic(BaseModel):
    name: str | None = None
    keyword: list[str] | None = None
    description: str | None = None

class SfxResponse(BaseModel):
    sound_effects: Dict[str, SfxEffect] = Field(description="Dictionary of sound effects with their properties")
    text: str = Field(description="Story text with embedded sound effect tags")
    bg_music: BgMusic = Field(description="Background music properties")

class Sfx:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        

        # # 4o
        # self.deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT')
        # api_key = os.getenv('AZURE_OPENAI_API_KEY')
        # azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT').rstrip('/')
        # api_version = "2024-08-01-preview"

        # self.client = AzureOpenAI(
        #     api_key=api_key,  
        #     azure_endpoint=azure_endpoint,
        #     api_version=api_version
        # )

        # o4mini
        self.deployment_name = "o4-mini"
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT_O4MINI")
        subscription_key = os.getenv("AZURE_OPENAI_API_KEY_O4MINI")
        api_version = "2024-12-01-preview"
        self.client = AzureOpenAI(
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=subscription_key,
        )

        # 4.1
        # self.deployment_name = "gpt-4.1"
        # endpoint = os.getenv("AZURE_OPENAI_ENDPOINT_O4MINI")
        # subscription_key = os.getenv("AZURE_OPENAI_API_KEY_O4MINI")
        # api_version = "2024-12-01-preview"
        # self.client = AzureOpenAI(
        #     api_version=api_version,
        #     azure_endpoint=endpoint,
        #     api_key=subscription_key,
        # )
    
    def generate(
        self, 
        title: str,
        text: str, 
        out_dir: str
    ) -> SfxResponse | None:
        # Generate opening first
        print("Generating opening...")
        opening = self.generate_opening(text)
        if not opening:
            print("Failed to generate opening")
            return None
        
        # Generate SFX with original text
        print("Generating SFX...")
        sfx_data = self.generate_sfx_with_database(text)
        if not sfx_data:
            print("Failed to generate SFX")
            return None
        
        # Add opening to the beginning of the SFX text
        sfx_data.text = f"<opening> {opening} <title> {title} <bg_music> {sfx_data.text}"


        sfx_data.sound_effects["opening"] = SfxEffect(
            name="toy-symphony",
            mode="opening"
        )
        sfx_data.sound_effects["title"] = SfxEffect(
            name="quirky-quest",
            mode="title"
        )
        sfx_data.sound_effects["bg_music"] = SfxEffect(
            name=sfx_data.bg_music.name,
            mode="bg_music"
        )

        # Save to file
        os.makedirs(out_dir, exist_ok=True)
        output_file = os.path.join(out_dir, "sfx_output.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(sfx_data.model_dump_json(indent=2))
        
        print(f"Successfully generated and saved SFX to {output_file}")
        return sfx_data.model_dump()
    
    def generate_opening(self, text: str) -> str | None:
        max_retries = 3
        messages = [
            {"role": "system", "content": OPENING_GENERATION_PROMPT},
            {"role": "user", "content": text}
        ]
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=messages,
                )
                
                opening = response.choices[0].message.content

                return opening.strip()
                
            except Exception as e:
                print(f"Attempt {attempt + 1}: Failed to generate opening - {str(e)}")
                
            if attempt < max_retries - 1:
                print("Retrying...")
            else:
                print("Max retries reached. Failed to generate opening.")
                return None
    
    # @observe()
    def generate_sfx_with_database(self, text: str) -> SfxResponse | None:
        max_retries = 3

        messages = [
            {
                "role": "system", 
                "content": SFX_GENERATION_WITH_DATABASE_PROMPT.format(
                    all_sfx_names=all_sfx_names,
                    all_bgm_names=all_bgm_names
                )
            },
            {"role": "user", "content": text}
        ]

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=messages,
                    response_format={"type": "json_object"},
                )
                
                content = response.choices[0].message.content
                messages.append({"role": "assistant", "content": content})
                
                # Validate using Pydantic
                sfx_data = SfxResponse.model_validate_json(content)

                # Extract all tags from the text
                tags = re.findall(r'<(\w+)>', sfx_data.text)
                
                # Check if all tags have corresponding sound effects
                missing_tags = [tag for tag in tags if tag not in sfx_data.sound_effects]
                if missing_tags:
                    raise ValueError(f"Tags found in text but missing from sound_effects: {missing_tags}")

                # # Check if all sound effects have corresponding tags
                # unused_effects = [effect for effect in sfx_data.sound_effects if effect not in tags]
                # if unused_effects:
                #     raise ValueError(f"Sound effects defined but not used in text: {unused_effects}")

                # Check if sound effects exist in database
                for effect_name, effect in sfx_data.sound_effects.items():
                    if effect_name not in ["opening", "title", "bg_music"]:  # Skip special effects
                        if effect.name not in all_sfx:
                            raise ValueError(f"Sound effect '{effect_name}' not found in database")

                # Check if background music exists in database
                if sfx_data.bg_music.name not in all_bgm:
                    raise ValueError(f"Background music '{sfx_data.bg_music.name}' not found in database")
                
                return sfx_data
                
            except Exception as e:
                error_message = f"The output is not valid, the error is: {str(e)}"
                print(f"Attempt {attempt + 1}: {error_message}")
                messages.append({"role": "user", "content": error_message})
            
            if attempt < max_retries - 1:
                print("Retrying...")
            else:
                print("Max retries reached. Failed to generate valid SFX.")
                return None


    def generate_sfx(self, text: str) -> SfxResponse | None:
        max_retries = 3
        messages = [
            {"role": "system", "content": SFX_CANDIDATES_GENERATION_PROMPT},
            {"role": "user", "content": text}
        ]
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=messages,
                    response_format={"type": "json_object"},
                )
                
                content = response.choices[0].message.content
                # Add the assistant's response to message history
                messages.append({"role": "assistant", "content": content})
                
                # Validate using Pydantic
                sfx_data = SfxResponse.model_validate_json(content)
                
                
                return sfx_data
                
            except Exception as e:
                error_message = f"The output is not valid, the error is: {str(e)}"
                print(f"Attempt {attempt + 1}: {error_message}")
                
                # Add error feedback to message history
                messages.append({"role": "user", "content": error_message})
            
            if attempt < max_retries - 1:
                print("Retrying...")
            else:
                print("Max retries reached. Failed to generate valid SFX.")
                return None


def parse_sfx_output(
    story_json: dict, 
    out_dir: str, 
    audio_files: dict[str, str],
) -> tuple[list[str], list[str]]:
    """
    Parse the SFX output and generate audio for each text segment between sound effects.
    
    Args:
        story_json: Dictionary containing the story text with sound effect tags
        out_dir: Output directory for the generated audio files
        sfx_files: Dictionary mapping sound effect names to their file paths
    
    Returns:
        Tuple containing:
        - List of file paths (both TTS and SFX) in the order they should be played
        - List of mixing instructions ("story", "overlay", or "exclusive") for each audio file
    """
    text = story_json["text"]
    
    # Split text by tags while keeping the tags
    parts = re.split(r'(<[\w-]+>)', text)
    
    # Process each part and build the audio path list
    current_text = ""
    segment_index = 0
    
    text_segments = []
    # Track where each text segment should be inserted in the final list
    text_positions = []
    audio_paths = []
    mixing_instructions = []
    position = 0
    
    for part in parts:
        if part.startswith('<') and part.endswith('>'):
            # Save accumulated text if any
            if current_text.strip():
                text_segments.append(current_text.strip())
                text_positions.append(position)
                position += 1
                current_text = ""
            
            # Add the sound effect file path
            sfx_name = part[1:-1]  # Remove < and >

            if "name" in story_json["sound_effects"][sfx_name]:
                # later retrieved
                sfx_file_name = story_json["sound_effects"][sfx_name]["name"]
            else:
                # directly generated
                sfx_file_name = sfx_name

            assert sfx_file_name in audio_files, \
                f"Sound effect {sfx_file_name} not found in audio files"
            mode = story_json["sound_effects"][sfx_name]["mode"]
            mixing_instructions.append(mode)
            audio_paths.append(audio_files[sfx_file_name])
            position += 1
        else:
            current_text += part
    
    # Handle any remaining text
    if current_text.strip():
        text_segments.append(current_text.strip())
        text_positions.append(position)
    
    # Generate audio for all text segments at once
    if text_segments:
        # First create the full lists with None placeholders for text segments
        final_audio_paths = [None] * (len(audio_paths) + len(text_segments))
        final_mixing_instructions = [None] * (len(audio_paths) + len(text_segments))
        
        # Copy over the sound effects
        current_sfx = 0
        for i in range(len(final_audio_paths)):
            if i not in text_positions:
                final_audio_paths[i] = audio_paths[current_sfx]
                final_mixing_instructions[i] = mixing_instructions[current_sfx]
                current_sfx += 1
        
        # Insert the text segment paths in their correct positions
        for i, pos in enumerate(text_positions):
            segment_path = os.path.join(out_dir, f"{i}.mp3")
            final_audio_paths[pos] = segment_path
            final_mixing_instructions[pos] = "story"
        
        audio_paths = final_audio_paths
        mixing_instructions = final_mixing_instructions
    
    json_dict = {
        "audio_paths": audio_paths,
        "mixing_instructions": mixing_instructions,
        "text_segments": text_segments
    }
    
    with open(f"{out_dir}/parsed_sfx_output.json", "w") as out:
        json.dump(json_dict, out, indent=4, ensure_ascii=False)
    
    return json_dict

if __name__ == "__main__":
    sfx = Sfx()
    sfx.generate("Alice in Wonderland", TEST_STORY, "out/alice")

    json_dict = json.load(open("out/alice/sfx_output.json"))

    json_dict = parse_sfx_output(json_dict, "out/alice", all_audio_files)
    print(json_dict)

    with open("out/alice/parsed_sfx_output.json", "w") as out:
        json.dump(json_dict, out, indent=4, ensure_ascii=False)
