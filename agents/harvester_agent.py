import requests
from bs4 import BeautifulSoup
import json
import os

# --- Configuration ---
SOURCES_FILE_PATH = 'config/sources.json'
OUTPUT_FILE_PATH = 'data/raw_album_list.json'
OUTPUT_DIR = 'data'

# --- Main Function ---
def harvest_new_albums():
    print("HarvesterAgent: Starting run...")
    
    # 1. Load the list of sources
    try:
        with open(SOURCES_FILE_PATH, 'r') as f:
            sources_config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Sources file not found at {SOURCES_FILE_PATH}")
        return
    
    raw_albums = []
    
    # 2. Loop through each source and fetch content
    for source in sources_config['sources']:
        source_name = source['name']
        source_url = source['url']
        
        print(f"\nScanning source: {source_name} ({source_url})")
        
        try:
            # We use a user-agent to look like a real browser
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
            response = requests.get(source_url, headers=headers, timeout=10)
            
            # Raise an error if the request failed
            response.raise_for_status() 
            
            # 3. Parse the HTML (THE HARD PART)
            # We pass the HTML content to a specific parsing function
            if "pitchfork" in source_url:
                # In the future, we'd call a specific parser
                # e.g., albums = parse_pitchfork(response.text)
                print("Note: Pitchfork parser not yet implemented.")
            elif "YourFavoriteBlog" in source_name:
                print("Note: 'YourFavoriteBlog' parser not yet implemented.")
            else:
                print("Note: No specific parser for this source.")
                
            # For now, we'll just add a placeholder
            # In a real run, 'albums' would be a list of dicts
            # e.g., albums = [{"artist": "Test", "album": "Test Album", "source": source_name}]
            albums = [] 
            
            if albums:
                raw_albums.extend(albums)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching {source_url}: {e}")

    # 4. Save the results to the output file
    # Ensure the 'data' directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True) 
    
    with open(OUTPUT_FILE_PATH, 'w') as f:
        json.dump(raw_albums, f, indent=2)
        
    print(f"\nHarvesterAgent: Run complete. Found {len(raw_albums)} new albums.")
    print(f"Results saved to {OUTPUT_FILE_PATH}")

# --- Run the script ---
if __name__ == "__main__":
    harvest_new_albums()
