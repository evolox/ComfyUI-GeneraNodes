import os
import shutil

# Define the source and destination directories
SOURCE_DIR = "./genera_ext"
DESTINATION_DIR = "../web/extensions/"

def copy_directory(src, dest):
    # Check if the source directory exists
    if not os.path.exists(src):
        print(f"Source directory {src} does not exist. Aborting.")
        return

    # Create the destination directory if it does not exist
    if not os.path.exists(dest):
        os.makedirs(dest)
        print(f"Created destination directory: {dest}")

    # Copy the directory
    try:
        shutil.copytree(src, dest, dirs_exist_ok=True)
        print(f"Successfully copied {src} to {dest}")
    except Exception as e:
        print(f"Failed to copy {src} to {dest}: {e}")

if __name__ == "__main__":
    copy_directory(SOURCE_DIR, DESTINATION_DIR)