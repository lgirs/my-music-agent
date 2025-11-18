import json
import os
import sys
import time
from dotenv import load_dotenv
from tidalapi import Session, exceptions as tidal_exceptions

# --- Configuration (Shared) ---
PLAYLIST_NAME = "Weekly Discovery"
OUTPUT_DIR = 'data'
PROCESSED_LOG_PATH = 'data/processed_albums.json' 

# --- Tidal Client (Reused from TidalAgent) ---
class RealTidalClient:
    def __init__(self):
        self.session = Session()
        load_dotenv(dotenv_path='config/.env') 
        token_type = os.getenv("TIDAL_TOKEN_TYPE")
        access_token = os.getenv("TIDAL_ACCESS_TOKEN")
        refresh_token = os.getenv("TIDAL_REFRESH_TOKEN")
        expiry_time = os.getenv("TIDAL_EXPIRY_TIME")
        if not all([token_type, access_token, refresh_token, expiry_time]):
            print("Error: Tidal auth tokens not found...")
            raise ValueError("Missing Tidal authentication")
        
        try:
            self.session.load_oauth_session(
                token_type=token_type,
                access_token=access_token,
                refresh_token=refresh_token,
                expiry_time=int(float(expiry_time))
            )
            self.user = self.session.user
        except Exception as e:
            print(f"Failed to authenticate with Tidal: {e}")
            raise

    def get_playlist(self, name):
        """Finds the 'Weekly Discovery' playlist object."""
        for pl in self.session.user.playlists():
            if pl.name == name:
                return pl
        return None

# --- Exclusion Log Management ---
def update_processed_log(artist, album, status="EXCLUDED_MANUAL"):
    """
    Updates the processed_albums.json file to permanently mark an album 
    as handled, overriding any previous ADDED or LIKED action if present.
    """
    try:
        with open(PROCESSED_LOG_PATH, 'r') as f:
            processed_albums = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        processed_albums = []

    unique_key = f"{artist}::{album}"
    
    # Check if album already exists in the log (it should, as the main agent added it)
    found = False
    for item in processed_albums:
        if item['key'] == unique_key:
            # Update the existing entry with the new exclusion status
            item['action'] = status 
            item['timestamp'] = time.time()
            found = True
            break
            
    # If somehow the album wasn't there, add it with the exclusion status
    if not found:
        processed_albums.append({
            "key": unique_key,
            "artist": artist,
            "album": album,
            "timestamp": time.time(),
            "action": status
        })
        
    with open(PROCESSED_LOG_PATH, 'w') as f:
        json.dump(processed_albums, f, indent=2)
        
    print(f"  > Log updated for '{artist} - {album}': Status set to {status}")

# --- Core Cleanup Function ---
def remove_album_from_playlist(artist, album_title, album_id, playlist_name):
    """
    Connects to Tidal, removes all tracks belonging to an album, and updates the exclusion log.
    """
    print(f"\nCleanupAgent: Removing '{album_title}' by '{artist}' (Album ID: {album_id})...")
    
    try:
        tidal_client = RealTidalClient()
    except Exception as e:
        print(f"Error: Cannot authenticate Tidal client. {e}")
        return False
        
    playlist = tidal_client.get_playlist(playlist_name)
    if not playlist:
        print(f"Error: Playlist '{playlist_name}' not found for user.")
        return False
        
    try:
        album_object = tidal_client.session.album(album_id)
        tracks = album_object.tracks()
        
        if not tracks:
            print("Warning: Could not find tracks for this album ID. Skipping removal.")
            update_processed_log(artist, album_title, status="EXCLUDED_MISSING_TRACKS")
            return True
            
        track_ids_to_remove = [track.id for track in tracks]
        
        # The tidalapi remove_by_id function removes tracks from the playlist
        # It's robust for removing multiple IDs at once.
        playlist.remove_by_id(track_ids_to_remove)
        
        print(f"  > SUCCESS: Removed {len(track_ids_to_remove)} tracks from '{playlist_name}'.")
        
        # Log this album as permanently EXCLUDED/handled
        update_processed_log(artist, album_title, status="EXCLUDED_MANUAL")
        return True
        
    except tidal_exceptions.ItemNotFound:
        print(f"Error: Album ID {album_id} not found on Tidal. Updating log to exclude.")
        update_processed_log(artist, album_title, status="EXCLUDED_NOT_FOUND")
        return True
    except Exception as e:
        print(f"An unexpected error occurred during removal: {e}")
        return False

# --- Entry Point for Manual/Future Workflow C Run ---
if __name__ == "__main__":
    # This section is a placeholder for how the new agent would be executed,
    # either via a dashboard or command line. We'll implement the web trigger later.
    print("CleanupAgent: Running in standalone mode.")
    # Example usage (hardcoded for demonstration - to be replaced by web interface calls)
    # Note: The real trigger will pass the album's artist and Tidal ID to this script.
    
    # Since we don't have the web trigger yet, this script will be empty on first run.
    # The next step will focus on creating the web interface to feed it data.
    pass
