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
    print("HarvesterAgent: Starting run (AI-Parser Mode)...")
    
    try:
        with open(SOURCES_FILE_PATH, 'r') as f:
            sources_config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Sources file not found at {SOURCES_FILE_PATH}")
        return
    
    # This is now a list of "pages to be read"
    pages_to_analyze = []
    
    # Loop through each source and fetch content
    for source in sources_config['sources']:
        
        # --- THIS IS THE FIX ---
        # We are using the 'website' key from your new sources file
        source_name = source['website'] 
        # --- END FIX ---
        
        source_url = source['url']
        
        print(f"\nFetching text from: {source_name} ({source_url})")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
            response = requests.get(source_url, headers=headers, timeout=15)
            response.raise_for_status() 
            
            # Use BeautifulSoup to get CLEAN text, not to parse
            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text(separator=' ', strip=True)
            
            if page_text:
                # We still save it as 'source_name' for the next agent
                pages_to_analyze.append({
                    "source_name": source_name,
                    "source_url": source_url,
                    "page_text": page_text # Just the clean text
                })
                print(f"  > Successfully fetched {len(page_text)} characters.")
            else:
                print("  > Found no text on page.")

        except requests.exceptions.RequestException as e:
            print(f"  > Error fetching {source_url}: {e}")

    # Save the results to the output file
    os.makedirs(OUTPUT_DIR, exist_ok=True) 
    
    with open(OUTPUT_FILE_PATH, 'w') as f:
        json.dump(pages_to_analyze, f, indent=2)
        
    print(f"\nHarvesterAgent: Run complete. Found {len(pages_to_analyze)} pages to analyze.")
    print(f"Results saved to {OUTPUT_FILE_PATH}")

# --- Run the script ---
if __name__ == "__main__":
    harvest_new_albums()
