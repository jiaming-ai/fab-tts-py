import os

def normalize_filenames(directories):
    """
    Transform filenames in given directories to use xx-xx format,
    replacing underscores and spaces with hyphens.
    
    Args:
        directories (list): List of directory paths to process
    """
    for directory in directories:
        if not os.path.exists(directory):
            print(f"Directory not found: {directory}")
            continue
            
        for filename in os.listdir(directory):
            # Get the full path of the file
            old_path = os.path.join(directory, filename)
            
            # Skip if it's a directory
            if os.path.isdir(old_path):
                continue
                
            # Replace underscores and spaces with hyphens, and convert to lowercase
            new_filename = filename.replace('_', '-').replace(' ', '-').lower()
            new_path = os.path.join(directory, new_filename)
            
            # Rename the file if the name has changed
            if new_filename != filename:
                try:
                    os.rename(old_path, new_path)
                    print(f"Renamed: {filename} -> {new_filename}")
                except OSError as e:
                    print(f"Error renaming {filename}: {e}")

# Example usage:
# dirs = ['/path/to/directory1', '/path/to/directory2']
# normalize_filenames(dirs)

dirs = ["data/sfx", "data/bg_music", "data/misc"]
normalize_filenames(dirs)
