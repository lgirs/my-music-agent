import requests
from bs4 import BeautifulSoup
import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
# --- NEW IMPORTS ---
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Configuration ---
SOURCES_FILE_PATH = 'config/sources.json'
OUTPUT_FILE_PATH = 'data/raw_album_list.json'
OUTPUT_DIR = 'data'

# --- Parser Functions (Unchanged) ---
# (Your parse_pitchfork and parse_rolling_stone functions go here)
# (No changes needed to them)

def parse_pitchfork(html_content, source_name):
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
                artist_name = artist_tag.get_text(strip=True)
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


# --- Main Function (HEAVILY UPDATED) ---
def harvest_new_albums():
    print("HarvesterAgent: Starting run...")
    
    # 1. Setup Selenium Driver
    print("  > Initializing headless Chrome driver...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    try:
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 15) # Set a 15-second max wait time
    except Exception as e:
        print(f"Error: Could not initialize Selenium driver: {e}")
        return

    # 2. Load the list of sources
    try:
        with open(SOURCES_FILE_PATH, 'r') as f:
            sources_config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Sources file not found at {SOURCES_FILE_PATH}")
        driver.quit()
        return
    
    raw_albums = []
    
    # 3. Loop through each source
    for source in sources_config['sources']:
        source_name = source['name']
        source_url = source['url']
        
        print(f"\nScanning source: {source_name} ({source_url})")
        
        try:
            driver.get(source_url)
            
            # --- THIS IS THE NEW LOGIC ---
            if "pitchfork.com" in source_url:
                print("  > Waiting for Pitchfork content to load...")
                # Wait until at least one review link is visible
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/reviews/albums/']")))
                print("  > Content loaded.")
                page_html = driver.page_source
                albums = parse_pitchfork(page_html, source_name)
                
            elif "rollingstone.com" in source_url:
                print("  > Waiting for Rolling Stone content to load...")
                # Wait until at least one 'article' tag is visible
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "article")))
                print("  > Content loaded.")
                page_html = driver.page_source
                albums = parse_rolling_stone(page_html, source_name)
            
            else:
                print(f"Note: No specific parser for this source: {source_name}")
                albums = []
            # --- END NEW LOGIC ---
            
            if albums:
                raw_albums.extend(albums)

        except Exception as e:
            # This now includes a 'TimeoutException' if the wait fails
            print(f"  > Error fetching or parsing {source_url}: {e}")

    # 4. Clean up and Save
    driver.quit() # Close the browser
    os.makedirs(OUTPUT_DIR, exist_ok=True) 
    
    with open(OUTPUT_FILE_PATH, 'w') as f:
        json.dump(raw_albums, f, indent=2)
        
    print(f"\nHarvesterAgent: Run complete. Found {len(raw_albums)} new albums.")
    print(f"Results saved to {OUTPUT_FILE_PATH}")

# --- Run the script ---
if __name__ == "__main__":
    harvest_new_albums()
