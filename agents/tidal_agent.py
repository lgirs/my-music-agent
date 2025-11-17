import json
import os
import time
from dotenv import load_dotenv
from tidalapi import Session, Quality
import tidalapi

# --- Configuration ---
INPUT_FILE_PATH = 'data/filtered_album_list.json'
LOG_FILE_PATH = 'data/run_log.txt'
OUTPUT_DIR = 'data'
PLAYLIST_NAME = "Weekly Discovery"
MAX_LIKED_ALBUMS_PER_RUN = 5 # <-- YOUR "MAX 5" RULE

# --- Real Tidal API Client ---
class RealTidalClient:
    def __init__(self):
        self.session = Session()
        token_type = os.getenv("TIDAL_TOKEN_TYPE")
        access_token = os.getenv("TIDAL_ACCESS_TOKEN")
        refresh_token = os.getenv("TIDAL_REFRESH_TOKEN")
        expiry_time = os.getenv("TIDAL_EXPIRY_TIME")

        if not all([token_type, access_token, refresh_token, expiry_time]):
            print("Error: Tidal auth tokens not found in config/.env or GitHub Secrets.")
            raise ValueError("Missing Tidal authentication")

        print("TidalActionAgent: Authenticating with Tidal...")
        try:
            self.session.load_oauth_session(
                token_type=token_type,
                access_token=access_token,
                refresh_token=refresh_token,
                expiry_time=int(float(expiry_time))
            )
            self.user = self.session.user
            print(f"Successfully authenticated as: {self.user.username}")
        except Exception as e:
            print(f"Failed to authenticate with Tidal: {e}")
            raise

    def find_album_id(self, artist, album):
        """Searches Tidal for an album and returns its ID."""
        print(f"  > Searching Tidal for: '{album}' by '{artist}'...")
        try:
            search_results = self.session.search(f"{artist} {album}", models=[tidalapi.Album])
            if search_results and search_results['albums']:
                first_album = search_results['albums'][0]
                print(f"  > Found album ID: {first_album.id}")
                return first_album.id
        except Exception as e:
            print(f"  > Error searching for album: {e}")
        return None

    def like_album(self, album_id, artist, album):
        """'Likes' an album by adding it to favorites."""
        print(f"  > ACTION: 'Liking' album (ID: {album_id}) - '{album}' by '{artist}'")
        try:
            self.session.user.favorites.add_album(album_id)
            return True
        except Exception as e:
            print(f"  > Error liking album: {e}")
            return False

    def add_album_to_playlist(self, album_id, artist, album, playlist_name):
        """Adds all tracks from an album to a specified playlist."""
        print(f"  > ACTION: Adding to playlist '{playlist_name}' (ID: {album_id}) - '{album}' by '{artist}'")
        try:
            album_object = self.session.album(album_id)
            tracks = album_object.tracks()
            track_ids = [track.id for track in tracks]
            
            playlist_id = None
            for pl in self.session.user.playlists():
                if pl.name == playlist_name:
                    playlist_id = pl.id
                    break
            
            if not playlist_id:
                print(f"  > Playlist '{playlist_name}' not found. Creating it...")
                new_pl = self.session.user.create_playlist(playlist_name, "Created by my AI agent.")
                playlist_id = new_pl.id

            # This is the corrected 'playlist' bug fix
            playlist = self.session.playlist(playlist_id)
            playlist.add(track_ids)
            print(f"  > Successfully added {len(track_ids)} tracks to '{playlist_name}'.")
            return True
        except Exception as e:
            print(f"  > Error adding to playlist: {e}")
            return False

def process_album_action(tidal_client, album_data):
    """A helper function to process a single album."""
    artist = album_data.get('artist')
    album = album_data.get('album')
    decision = album_data.get('decision')
    
    if not artist or not album:
        print(f"  > Skipping invalid entry: {album_data}")
        return f"SKIPPED_INVALID: {album_data}"

    album_id = tidal_client.find_album_id(artist, album)
    if not album_id:
        print(f"  > Could not find '{album}' on Tidal. Skipping.")
        return f"NOT_FOUND: '{album}' by '{artist}'"
        
    try:
        if decision == "LIKE_IMMEDIATELY":
            tidal_client.like_album(album_id, artist, album)
            return f"LIKED: '{album}' by '{artist}'"
            
        elif decision == "ADD_TO_PLAYLIST":
            tidal_client.add_album_to_playlist(album_id, artist, album, playlist_name=PLAYLIST_NAME)
            return f"ADDED_TO_PLAYLIST: '{album}' by '{artist}'"
            
    except Exception as e:
        print(f"  > Error during Tidal action: {e}")
        return f"ERROR: '{album}' by '{artist}' - {e}"

# --- Main Function (UPDATED WITH NEW LOGIC) ---
def take_tidal_actions():
    print("TidalActionAgent: Starting run...")
    
    try:
        tidal_client = RealTidalClient()
    except Exception as e:
        print(f"Could not start Tidal agent. Exiting. Error: {e}")
        return

    try:
        with open(INPUT_FILE_PATH, 'r') as f:
            filtered_albums = json.load(f)
        print(f"Found {len(filtered_albums)} approved albums to process.")
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Note: Filtered albums file not found or empty. No actions to take.")
        return
    
    # --- THIS IS YOUR NEW "MAX 5" FEATURE ---
    # 1. Separate albums based on the AI's decision
    albums_to_like = [a for a in filtered_albums if a.get('decision') == 'LIKE_IMMEDIATELY']
    albums_to_playlist = [a for a in filtered_albums if a.get('decision') == 'ADD_TO_PLAYLIST']

    # 2. Sort the "Like" list by score (highest first)
    albums_to_like.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    print(f"  > Found {len(albums_to_like)} albums to 'Like' and {len(albums_to_playlist)} to 'Add to Playlist'.")

    # 3. Cap *only* the "Like" list
    if len(albums_to_like) > MAX_LIKED_ALBUMS_PER_RUN:
        print(f"  > Capping 'Like' list from {len(albums_to_like)} to the top {MAX_LIKED_ALBUMS_PER_RUN} most relevant.")
        albums_to_like = albums_to_like[:MAX_LIKED_ALBUMS_PER_RUN]
    # --- END NEW FEATURE ---

    actions_taken = []
    
    # Process the (now capped) "Like" list
    print(f"\n--- Processing {len(albums_to_like)} 'Like' Actions ---")
    for album_data in albums_to_like:
        action_result = process_album_action(tidal_client, album_data)
        actions_taken.append(action_result)

    # Process the (full) "Playlist" list
    print(f"\n--- Processing {len(albums_to_playlist)} 'Playlist' Actions ---")
    for album_data in albums_to_playlist:
        action_result = process_album_action(tidal_client, album_data)
        actions_taken.append(action_result)

    # --- Log all actions ---
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(LOG_FILE_PATH, 'a') as f:
        f.write(f"\n--- TidalAgent Run: {time.ctime()} ---\n")
        for action in actions_taken:
            f.write(f"{action}\n")
            
    print(f"\nTidalActionAgent: Run complete. Processed {len(actions_taken)} total actions.")
    print(f"Actions logged to {LOG_FILE_PATH}")

if __name__ == "__main__":
    take_tidal_actions()
