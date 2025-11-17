import requests
from bs4 import BeautifulSoup
import json
import os

# --- Configuration ---
SOURCES_FILE_PATH = 'config/sources.json'
OUTPUT_FILE_PATH = 'data/raw_album_list.json'
OUTPUT_DIR = 'data'

def parse_pitchfork(html_content, source_name):
    """
    Parses the Pitchfork /reviews/albums/ page HTML
    and extracts artist and album names.
    """
    print(f"  > Running Pitchfork-specific parser...")
    albums_found = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all the review "cards" on the page
    # Pitchfork wraps each review in a 'div' with a class 'review'
    review_cards = soup.find_all('div', class_='review')
    
    if not review_cards:
        print("  > No review cards found. (HTML structure might have changed?)")
        return []

    for card in review_cards:
        try:
            # The artist name is in a 'ul' with class 'artist-list'
            artist_name = card.find('ul', class_='artist-list').get_text(strip=True)
            
            # The album title is in an 'h2' tag
            album_title = card.find('h2').get_text(strip=True)
            
            if artist_name and album_title:
                albums_found.append({
                    "artist": artist_name,
                    "album": album_title,
                    "source": source_name
                })
        except AttributeError:
            # If a card is missing an artist or album (e.g., it's a 'Various Artists'
            # compilation without a clear tag), we just skip it.
            continue
            
    print(f"  > Found {len(albums_found)} albums on Pitchfork.")
    return albums_found


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
            
            albums = [] # Initialize our list for this source
            
            if "pitchfork.com" in source_url:
                albums = parse_pitchfork(response.text, source_name)
                
            elif "rollingstone.com" in source_url:
                # We'll build this one next
                print(f"Note: 'Rolling Stone' parser not yet implemented.")
            
            else:
                print(f"Note: No specific parser for this source: {source_name}")
            
            
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
