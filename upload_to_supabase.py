import os
import glob
from supabase import create_client
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables or .env file")

supabase = create_client(supabase_url, supabase_key)

def create_bucket_if_not_exists(bucket_name):
    """Create a bucket if it doesn't exist"""
    try:
        # Check if bucket exists
        supabase.storage.get_bucket(bucket_name)
        print(f"Bucket '{bucket_name}' already exists")
    except Exception:
        # Create bucket if it doesn't exist
        supabase.storage.create_bucket(bucket_name)
        print(f"Created bucket '{bucket_name}'")

def upload_audio_files():
    """Upload all mixed.mp3 files to Supabase storage"""
    # Create bucket if it doesn't exist
    bucket_name = "audios"
    create_bucket_if_not_exists(bucket_name)
    
    # Find all mixed.mp3 files
    audio_files = glob.glob("out/audios/**/mixed.mp3", recursive=True)
    
    uploaded_urls = []
    
    for audio_path in audio_files:
        # Extract story name from directory path
        dir_name = os.path.basename(os.path.dirname(audio_path))
        
        # Sanitize filename - replace apostrophes and other problematic characters
        sanitized_name = dir_name.replace("'", "").replace(" ", "_").lower()
        file_name = f"{sanitized_name}.mp3"
        
        print(f"Processing {audio_path} as {file_name}...")
        
        try:
            # Check if file already exists
            try:
                supabase.storage.from_(bucket_name).get_public_url(file_name)
                print(f"File {file_name} already exists, skipping...")
                
                # Still add to our list of URLs
                file_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
                uploaded_urls.append({
                    "story_name": dir_name,
                    "file_name": file_name,
                    "url": file_url
                })
                continue
            except Exception:
                # File doesn't exist, proceed with upload
                pass
            
            # Upload file to Supabase
            with open(audio_path, 'rb') as f:
                supabase.storage.from_(bucket_name).upload(
                    file_name,
                    f.read(),
                    {"content-type": "audio/mpeg", "cacheControl": "3600"}
                )
            
            # Get public URL
            file_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
            uploaded_urls.append({
                "story_name": dir_name,
                "file_name": file_name,
                "url": file_url
            })
            print(f"Successfully uploaded {file_name}")
            
        except Exception as e:
            print(f"Error uploading {file_name}: {e}")
    
    return uploaded_urls

def main():
    """Main function to upload files and save URLs"""
    print("Starting audio file upload to Supabase...")
    
    uploaded_urls = upload_audio_files()
    
    # Save URLs to file
    output_file = "uploaded_audio_urls.json"
    with open(output_file, 'w') as f:
        json.dump(uploaded_urls, f, indent=2)
    
    print(f"Uploaded {len(uploaded_urls)} files. URLs saved to {output_file}")
    
    return uploaded_urls

if __name__ == "__main__":
    main() 