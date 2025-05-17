import json
import os
from pydub import AudioSegment

def load_audio_file(file_path):
    """
    Load an audio file with fallback to explicit codec if needed.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        AudioSegment object
    """
    try:
        return AudioSegment.from_file(file_path)
    except Exception as e:
        try:
            return AudioSegment.from_file(file_path, format="wav", codec="adpcm_ms")
        except Exception as inner_e:
            raise Exception(f"Failed to load audio file {file_path}: {str(e)}, then tried with codec: {str(inner_e)}")

def mix_audio(parsed_sfx_output: dict, out_path: str):
    """
    Mix audio files according to specified modes.
    
    Args:
        parsed_sfx_output: Parsed SFX output
        out_path: Output path for the mixed audio file
    """
    audio_paths = parsed_sfx_output["audio_paths"]
    mixing_modes = parsed_sfx_output["mixing_instructions"]

    if len(audio_paths) != len(mixing_modes):
        raise ValueError("audio_paths and mixing_modes must have the same length")
    
    # Initialize empty result
    mixed = AudioSegment.empty()
    bg_audio = None
    bg_start_timestamp = 0
    
    i = 0
    while i < len(audio_paths):
        current_path = audio_paths[i]
        current_mode = mixing_modes[i]
        
        # Load current audio
        current_audio = load_audio_file(current_path)
        
        if current_mode == "opening":
            # Initial 3 seconds at full volume
            current_audio = current_audio[6000:] -5 # Skip first 6 seconds
            mixed += current_audio[:3000]
            
            if i + 1 < len(audio_paths):
                # Load next story segment
                next_story = load_audio_file(audio_paths[i + 1])
                
                # Create background music with fade from full to reduced volume
                bg_music = current_audio[3000:3000 + len(next_story)]
                fade_duration = 2000  # 2 second fade
                
                # Apply crossfade between full and reduced volume
                full_vol = bg_music[:fade_duration]
                reduced_vol = (bg_music[:fade_duration] - 15)  # Reduced by 15dB
                faded_start = full_vol.fade_out(fade_duration).overlay(reduced_vol.fade_in(fade_duration))
                
                # Combine faded start with remaining reduced volume section
                bg_music = faded_start + (bg_music[fade_duration:] - 15)
                
                # Mix with story
                mixed = mixed + next_story.overlay(bg_music)
                
                # Add final transition: fade in to full volume, hold, then fade out
                final_bg = current_audio[3000 + len(next_story):3000 + len(next_story) + 6000]
                if len(final_bg) > 0:
                    fade_up = (final_bg[:2000] - 15).fade_out(2000).overlay(final_bg[:2000].fade_in(2000))
                    full_vol = final_bg[2000:4000]  # 2 seconds at full volume
                    fade_out = final_bg[4000:6000].fade_out(2000)  # 2 second fade out
                    mixed += fade_up + full_vol + fade_out
                
                i += 1  # Skip next segment as we've processed it
            
        elif current_mode == "title":
            next_audio = load_audio_file(audio_paths[i + 1])
            silence = AudioSegment.silent(duration=1000)
            mixed += silence
            mixed += next_audio
            # Add 3 seconds of silence
            silence = AudioSegment.silent(duration=3000)
            mixed += silence
            i += 1
            
        elif current_mode == "bg_music":
            # Save the background music and current timestamp
            bg_audio = current_audio

            bg_start_timestamp = len(mixed)

            # # Add 3 seconds of silence
            # silence = AudioSegment.silent(duration=3000)
            # mixed += silence
            
        elif current_mode == "story":
            # Simply append story segments
            mixed += current_audio
            
        elif current_mode == "exclusive":
            # Limit to 5 seconds with fade out
            sfx = current_audio[:5000]  # 5 seconds
            if len(sfx) > 3000:  # If longer than 3 seconds, apply fade out
                sfx = sfx.fade_out(2000)  # 2 second fade out
            mixed += sfx
            
        elif current_mode == "overlay":
            sfx = current_audio
            if i + 1 < len(audio_paths) and mixing_modes[i + 1] == "story":
                # Load next story segment
                next_story = load_audio_file(audio_paths[i + 1])
                
                # First 3 seconds at full volume
                initial_sfx = sfx[:3000]
                mixed += initial_sfx
                
                # Remaining overlay with reduced volume
                remaining_duration = min(6000, len(next_story))  # 6 seconds or story length
                if remaining_duration > 0:
                    overlay_sfx = sfx[3000:3000 + remaining_duration] - 10  # Reduce volume by 10dB
                    story_segment = next_story[:remaining_duration]
                    
                    # Overlay the sounds
                    mixed = mixed + story_segment.overlay(overlay_sfx)
                
                # Add any remaining story audio
                if len(next_story) > remaining_duration:
                    mixed += next_story[remaining_duration:]
                
                # Skip the next story segment since we've already processed it
                i += 1
            else:
                # If no next story segment, treat as exclusive
                sfx = sfx[:5000].fade_out(2000)
                mixed += sfx
        
        i += 1
    
    # After all segments are processed, mix in the background music if it exists
    if bg_audio is not None:
        bg_audio = bg_audio
        
        total_length = len(mixed) - bg_start_timestamp

        # Calculate minimum loops needed for background music
        min_loops = (total_length // len(bg_audio)) + 1
        extended_bg_audio = bg_audio * min_loops  # Extend background music by looping

        
        # Create the background segment
        bg_segment = AudioSegment.empty()
        
        # First 3 seconds at full volume
        bg_segment += bg_audio[:3000]
        
        # Create fade transition and reduced volume section
        main_bg = extended_bg_audio[3000:3000 + total_length - 6000]  # Leave room for final transition
        fade_duration = 2000
        
        # Fade from full to reduced volume
        full_vol = main_bg[:fade_duration]
        reduced_vol = (main_bg[:fade_duration] - 15)
        faded_start = full_vol.fade_out(fade_duration).overlay(reduced_vol.fade_in(fade_duration))
        
        # Add faded start and reduced volume section
        bg_segment += faded_start + (main_bg[fade_duration:] - 15)
        
        # Add final transition back to full volume and fade out
        final_bg = extended_bg_audio[3000 + len(main_bg):3000 + len(main_bg) + 6000]
        if len(final_bg) > 0:
            fade_up = (final_bg[:2000] - 15).fade_out(2000).overlay(final_bg[:2000].fade_in(2000))
            full_vol = final_bg[2000:4000]  # 2 seconds at full volume
            fade_out = final_bg[4000:6000].fade_out(2000)  # 2 second fade out
            bg_segment += fade_up + full_vol + fade_out
        
        # Mix the background with the main audio
        final_mixed = mixed[:bg_start_timestamp]
        final_mixed += mixed[bg_start_timestamp:].overlay(bg_segment)
        mixed = final_mixed

    # Export the final mixed audio
    mixed.export(out_path, format="mp3")

    return out_path

def read_tts_audio(audio_dir: str):
    """Read all .wav files in the given directory.
    Returns a list of file paths, sorted by filename.
    """
    files = []
    for fname in os.listdir(audio_dir):
        if fname.endswith(".wav"):
            files.append(os.path.join(audio_dir, fname))
    return sorted(files)

# def read_sfx_text(sfx_path: str) -> list[dict]:
#     """Read and parse the text from sfx_output.json file.
#     Returns a list of dictionaries with structure:
#     [
#         {"type": "text", "value": "some text"},
#         {"type": "sfx", "value": "sound_effect_name"},
#         ...
#     ]
#     """
#     # Read the JSON file
#     with open(sfx_path, "r") as f:
#         data = json.load(f)
    
#     text = data["text"]
#     result = []
    
#     # Split by < and > to separate text and sound effects
#     parts = text.replace("</", "<").split("<")
    
#     for part in parts:
#         if not part.strip():
#             continue
            
#         if ">" in part:
#             # Handle sound effect
#             sfx_name = part.split(">")[0].strip()
#             remaining_text = part.split(">")[1].strip()
            
#             if sfx_name:
#                 result.append({"type": "sfx", "value": sfx_name})
#             if remaining_text:
#                 result.append({"type": "text", "value": remaining_text})
#         else:
#             # Handle regular text
#             if part.strip():
#                 result.append({"type": "text", "value": part.strip()})
    
#     return result


# def retrive_sfx_audio(sfx_name: str, sfx_dir: str) -> str:
#     """Retrieve the audio file for the given sound effect name."""
#     for fname in os.listdir(sfx_dir):
#         if fname.startswith(sfx_name):
#             return os.path.join(sfx_dir, fname)
#     return None

if __name__ == "__main__":
    # files = read_tts_audio("out/alice")
    # print(files)

    with open("out/alice/parsed_sfx_output.json", "r", encoding='utf-8') as f:
        json_dict = json.load(f)

    mix_audio(json_dict, "out/alice/mixed.mp3")

