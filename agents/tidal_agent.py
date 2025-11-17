import json
import os
import time

# --- Configuration ---
INPUT_FILE_PATH = 'data/filtered_album_list.json'
LOG_FILE_PATH = 'data/run_log.txt' # We'll log our actions here
OUTPUT_DIR = 'data'

# --- Placeholder for Tidal API Connection ---
# We'll group our mock API calls into a class
# to make it easy to replace with the real API later.

class MockTidalClient:
    def __init__(self, auth_token="dummy_token"):
        print(f"MockTidalClient: Authenticated (using {auth_token}).")
        
    def find_album_id(self, artist, album):
        """ Simulates searching Tidal for an album ID. """
        print(f"  > Searching Tidal for: '{album}' by '{artist}'...")
        time.sleep(0.2)
        # Return a fake ID
        return f"tidal-id-{hash(artist + album)}" 

    def like_album(self, album_id, artist, album):
        """ Simulates 'Liking' an album. """
        print(f"  > ACTION: 'Liking' album (ID: {album_id}) - '{album}' by '{artist}'")
        return True

    def add_album_to_playlist(self, album_id, artist, album, playlist_name="Weekly Discovery"):
        """ Simulates adding an album to a playlist. """
        print(f"  > ACTION: Adding to playlist '{playlist_name}' (ID: {album_id}) - '{album}' by '{artist}'")
        return True

# --- Main Function ---
def take_tidal_actions():
    print("TidalActionAgent: Starting run...")
    
    # 1. Initialize our (mock) Tidal client
    # In the future, we'd pass a real auth token from config/.env
    tidal_client = MockTidalClient()

    # 2. Load the filtered albums list
    try:
        with open(INPUT_FILE_PATH, 'r') as f:
            filtered_albums = json.load(f)
        print(f"Found {len(filtered_albums)} approved albums to process.")
    except FileNotFoundError:
        print(f"Note: Filtered albums file not found at {INPUT_FILE_PATH}. No actions to take.")
        return # Exit if there's nothing to do
    except json.JSONDecodeError:
        print(f"Error: Could not decode {INPUT_FILE_PATH}. No actions to take.")
        return

    # 3. Process each approved album
    actions_taken = []
    for album_data in filtered_albums:
        artist = album_data.get('artist')
        album = album_data.get('album')
        decision = album_data.get('decision')
        
        if not artist or not album:
            print(f"  > Skipping invalid entry: {album_data}")
            continue

        print(f"\nProcessing '{album}' by '{artist}'...")
        
        # Step 3a: Find the album on Tidal
        album_id = tidal_client.find_album_id(artist, album)
        
        if not album_id:
            print(f"  > Could not find album on Tidal. Skipping.")
            actions_taken.append(f"NOT_FOUND: '{album}' by '{artist}'")
            continue
            
        # Step 3b: Perform the action based on the decision
        try:
            if decision == "LIKE_IMMEDIATELY":
                tidal_client.like_album(album_id, artist, album)
                actions_taken.append(f"LIKED: '{album}' by '{artist}'")
                
            elif decision == "ADD_TO_PLAYLIST":
                # You could make the playlist name dynamic (e.g., based on the date)
                tidal_client.add_album_to_playlist(album_id, artist, album, playlist_name="Weekly Discovery")
                actions_taken.append(f"ADDED_TO_PLAYLIST: '{album}' by '{artist}'")
                
        except Exception as e:
            print(f"  > Error during Tidal action: {e}")
            actions_taken.append(f"ERROR: '{album}' by '{artist}' - {e}")

    # 4. Log our actions
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(LOG_FILE_PATH, 'a') as f: # 'a' means append to the log
        f.write(f"\n--- TidalAgent Run: {time.ctime()} ---\n")
        for action in actions_taken:
            f.write(f"{action}\n")
            
    print(f"\nTidalActionAgent: Run complete. Processed {len(filtered_albums)} albums.")
    print(f"Actions logged to {LOG_FILE_PATH}")

# --- Run the script ---
if __name__ == "__main__":
    take_tidal_actions()
