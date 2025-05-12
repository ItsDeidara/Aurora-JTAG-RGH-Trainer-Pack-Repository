import json
import os
import tkinter as tk
from tkinter import filedialog
import requests
from pathlib import Path
import re
import time
import sys

def load_json_from_github(url):
    """
    Load JSON data from a GitHub raw URL
    """
    try:
        print(f"Downloading JSON data from {url}...")
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # The data seems to be in a non-standard JSON format (multiple JSON objects without being in an array)
        # Let's fix that by wrapping it in square brackets and fixing comma issues
        content = response.text.strip()
        if content.startswith("{") and not content.startswith("[{"):
            content = "[" + content + "]"
            # Replace multiple consecutive commas with a single comma
            content = re.sub(r',\s*,', ',', content)
            # Ensure we don't have a trailing comma before closing bracket
            content = re.sub(r',\s*\]', ']', content)
        
        return json.loads(content)
    except requests.exceptions.RequestException as e:
        print(f"Error loading JSON from URL: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print("JSON content might be malformed. Let's try a different approach.")
        
        # Alternative parsing for non-standard JSON format
        try:
            # This specifically handles the format shown in the example
            fixed_content = "[" + response.text.replace("}, {", "},{") + "]"
            return json.loads(fixed_content)
        except json.JSONDecodeError:
            print("Still couldn't parse the JSON. Please ensure the URL provides valid JSON data.")
            return None

def browse_folder():
    """
    Open a file dialog to select a folder
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    
    folder_path = filedialog.askdirectory(title="Select the folder containing game directories")
    
    if not folder_path:
        print("No folder selected. Exiting.")
        return None
    
    print(f"Selected folder: {folder_path}")
    return folder_path

def scan_folder_for_titleids(folder_path, title_data):
    """
    Scan the folder for directories named after TitleIDs with improved performance and debug info
    """
    # Create a dictionary for fast lookup of titles by TitleID
    title_dict = {item["TitleID"].lower(): (item["TitleID"], item["Title"]) for item in title_data}
    
    found_games = []
    total_dirs = 0
    start_time = time.time()
    last_update_time = start_time
    
    print(f"\nScanning for {len(title_dict)} different TitleIDs...")
    
    try:
        # Walk through all directories in the folder
        for root, dirs, files in os.walk(folder_path):
            for dir_name in dirs:
                total_dirs += 1
                dir_lower = dir_name.lower()
                
                # More efficient check - first check if any TitleID is contained in the directory name
                # This approach is much faster for folders containing many titles
                matched = False
                for title_id_lower, (original_id, title) in title_dict.items():
                    if title_id_lower in dir_lower:
                        found_games.append(f"{original_id}: {title}")
                        print(f"Found game: {original_id} - {title}")
                        matched = True
                        break
                
                # Print progress more frequently with time estimates
                current_time = time.time()
                if total_dirs % 20 == 0 or (current_time - last_update_time) > 5:
                    elapsed = current_time - start_time
                    rate = total_dirs / elapsed if elapsed > 0 else 0
                    print(f"Processed {total_dirs} directories ({rate:.1f} dirs/sec), found {len(found_games)} games...")
                    last_update_time = current_time
    
    except Exception as e:
        print(f"Error during scanning: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"Finished scanning {total_dirs} directories in {time.time() - start_time:.1f} seconds.")
    
    # Sort found games by title for better organization
    found_games.sort(key=lambda x: x.split(": ", 1)[1] if ": " in x else x)
    
    return found_games

def save_results(found_games, output_file="supported_games.md"):
    """
    Save the list of found games to a Markdown file formatted for GitHub
    """
    # Sort games alphabetically by title
    sorted_games = sorted(found_games, key=lambda x: x.split(": ", 1)[1] if ": " in x else x)
    
    with open(output_file, "w") as f:
        # Write a nice header
        f.write("# Xbox 360 Supported Games\n\n")
        f.write(f"This list contains {len(found_games)} Xbox 360 games found in the local collection.\n\n")
        
        # Add a timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"*Generated on: {timestamp}*\n\n")
        
        # Create a table
        f.write("| Title ID | Game Title |\n")
        f.write("|----------|------------|\n")
        
        # Write each game as a table row
        for game in sorted_games:
            if ": " in game:
                title_id, title = game.split(": ", 1)
                f.write(f"| {title_id} | {title} |\n")
            else:
                f.write(f"| Unknown | {game} |\n")
    
    print(f"Results saved to {output_file}")

def main():
    print("Game Finder - Find supported games in your folder")
    print("=" * 50)
    
    # Use the specified GitHub raw URL
    github_url = "https://gist.githubusercontent.com/albertofustinoni/51f2ea0537130f4820a3f5ed49d69042/raw/9ffead88e369a40e120082ef385efea6fc1cbb81/Xbox360TitleIDs.json"
    print(f"Using JSON file from: {github_url}")
    
    # Load the JSON data
    title_data = load_json_from_github(github_url)
    
    if not title_data:
        print("Failed to load title data. Please check the URL and try again.")
        return
    
    print(f"Successfully loaded {len(title_data)} game titles from JSON.")
    
    # Ask the user to browse for the folder
    print("\nPlease select the folder containing game directories...")
    folder_path = browse_folder()
    
    if not folder_path:
        return
    
    # Confirm the folder selection
    confirm = input(f"Confirm scan of folder: {folder_path}? (y/n): ").lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    # Scan the folder for TitleIDs
    print("\nScanning folder for game directories...")
    try:
        found_games = scan_folder_for_titleids(folder_path, title_data)
        
        # Save the results
        if found_games:
            save_results(found_games)
            print(f"\nFound {len(found_games)} games out of {len(title_data)} titles.")
            print(f"Results saved as a Markdown file for GitHub. You can view it by opening supported_games.md or uploading it to GitHub.")
        else:
            print("\nNo matching games found in the selected folder.")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()