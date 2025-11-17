import requests
from bs4 import BeautifulSoup
import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# --- Configuration ---
SOURCES_FILE_PATH = 'config/sources.json'
OUTPUT_FILE_PATH = 'data/raw_album_list.json'
OUTPUT_DIR = 'data'

# --- NEW: Selenium Helper Function ---
def get_page_with_selenium(url):
    """
    Uses a headless Chrome browser (Selenium) to fetch a
    JavaScript-rendered page.
    """
    print(f"  > Fetching with Selenium (headless browser)...")
    options = Options()
    options.add_argument("--headless") # Run invisibly
    options.add_argument("--no-sandbox") # Required for GitHub Actions
    options.add_argument("--disable-dev-shm-usage") # Required for GitHub Actions
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36")
    
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(url)
        # Wait 5 seconds for all the JavaScript to load
        time.sleep(5) 
        html_content = driver.page_source
        return html_content
    finally:
        driver.quit()

# --- Your Parser Functions (Unchanged) ---

def parse_pitchfork(html_content, source_name):
    """
    (Updated) Parses the Pitchfork /reviews/albums/ page HTML.
    """
    print(f"  > Running Pitchfork-specific parser...")
    albums_found = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    review_links = soup.find_all('a', href=lambda href: href and href.startswith('/reviews/albums/'))
    
    if not review_links:
        print("  > No review links found. (HTML structure might have changed?)")
        return []

    for link in review_links:
        try:
            artist_tag = link.find('ul', class_=lambda c: c and c.startswith('ArtistList-'))
            if not artist_tag:
                artist_tag = link.find('div', class_=lambda c: c and c.startswith('ReviewCardArtist-'))
            
            album_tag = link.find('h2', class_=lambda c: c and c.startswith('ReviewCardAlbumName-'))
            
            if artist_tag and album_tag:
                artist_name = artist_tag.get_text(stripTrue=True)
                album_title = album_tag.get_text(strip=True)
                
                if {"artist": artist_name, "album": album_title, "source": source_name} not in albums_found:
                    albums_found.append({
                        "artist": artist_name,
                        "album": album_title,
                        "source": source_name
                    })
        except AttributeError:
            continue
            
    print(f"  > Found {len(albums_found)} albums on Pitchfork.")
    return albums_found


def parse_rolling_stone(html_content, source_name):
    """
    (Updated) Parses the Rolling Stone /music-album-reviews/ page HTML.
    """
    print(f"  > Running Rolling Stone-specific parser...")
    albums_found = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    review_cards = soup.find_all('article', class_=lambda c: c and c.startswith('story-'))
    
    if not review_cards:
        print("  > No 'article' tags found. (HTML structure might have changed?)")
        return []

    for card in review_cards:
        try:
            artist_tag = card.find('p', class_=lambda c: c and 'kicker' in c)
            album_tag = card.find('h3', class_=lambda c: c and 'title' in c)
            
            if artist_tag and album_tag:
                artist_name = artist_tag.get_text(strip=True)
                album_title = album_tag.get_text(strip=True)
                
                if album_title.lower().startswith(artist_name.lower()):
                    album_title = album_title[len(artist_name):].lstrip(":' ")
                
                albums_found.append({
                    "artist": artist_name,
                    "album": album_title,
                    "source": source_name
                })
        except AttributeError:
            continue
            
    print(f"  > Found {len(albums_found)} albums on Rolling Stone.")
    return albums_found

# --- Main Function (UPDATED) ---
def harvest_new_albums():
    print("HarvesterAgent: Starting run...")
    
    try:
        with open(SOURCES_FILE_PATH, 'r') as f:
            sources_config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Sources file not found at {SOURCES_FILE_PATH}")
        return
    
    raw_albums = []
    
    for source in sources_config['sources']:
        source_name = source['name']
        source_url = source['url']
        
        print(f"\nScanning source: {source_name} ({source_url})")
        
        try:
            # --- THIS IS THE BIG CHANGE ---
            # We now use Selenium to get the page
            page_html = get_page_with_selenium(source_url)
            # --- END CHANGE ---
            
            albums = [] 
            
            if "pitchfork.com" in source_url:
                albums = parse_pitchfork(page_html, source_name)
                
            elif "rollingstone.com" in source_url:
                albums = parse_rolling_stone(page_html, source_name)
            
            else:
                print(f"Note: No specific parser for this source: {source_name}")
            
            if albums:
                raw_albums.extend(albums)

        except Exception as e:
            print(f"Error fetching {source_url}: {e}")

    os.makedirs(OUTPUT_DIR, exist_ok=True) 
    
    with open(OUTPUT_FILE_PATH, 'w') as f:
        json.dump(raw_albums, f, indent=2)
        
    print(f"\nHarvesterAgent: Run complete. Found {len(raw_albums)} new albums.")
    print(f"Results saved to {OUTPUT_FILE_PATH}")

# --- Run the script ---
if __name__ == "__main__":
    harvest_new_albums()
