import json
import os
import sys
import time
from dotenv import load_dotenv
from tidalapi import Session, exceptions as tidal_exceptions

# --- Configuration ---
PLAYLIST_NAME = "Weekly Discovery"
PROCESSED_LOG_PATH = 'data/processed_albums.json' 

class RealTidalClient:
    def __init__(self):
        self.session = Session()
        load_dotenv(dotenv_path='config/.env') 
        token_type = os.getenv("TIDAL_TOKEN_TYPE")
        access_token = os.getenv("TIDAL_ACCESS_TOKEN")
        refresh_token = os.getenv("TIDAL_REFRESH_TOKEN")
        expiry_time = os.getenv("TIDAL_EXPIRY_TIME")
        if not all([token_type, access_token, refresh_token, expiry_time]):
            print("Error: Tidal auth tokens not found.")
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
        for pl in self.session.user.playlists():
            if pl.name == name:
                return pl
        return None

    def like_album(self, album_id):
        print(f"  > Liking album {album_id}...")
        self.session.user.favorites.add_album(album_id)

def update_processed_log(artist, album, status):
    try:
        with open(PROCESSED_LOG_PATH, 'r') as f:
            processed_albums = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        processed_albums = []

    unique_key = f"{artist}::{album}"
    found = False
    for item in processed_albums:
        if item['key'] == unique_key:
            item['action'] = status 
            item['timestamp'] = time.time()
            found = True
            break
            
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
    print(f"  > Log updated: {unique_key} -> {status}")

def handle_album_action(artist, album_title, album_id, action_type):
    print(f"\nCleanupAgent: Processing '{album_title}' by '{artist}' (ID: {album_id})")
    print(f"  > Action: {action_type}")
    
    try:
        tidal_client = RealTidalClient()
    except Exception:
        return False
        
    playlist = tidal_client.get_playlist(PLAYLIST_NAME)
    if not playlist:
        print(f"Error: Playlist '{PLAYLIST_NAME}' not found.")
        return False
        
    try:
        # 1. If Promoting, Like the album first
        if action_type == "PROMOTE":
            tidal_client.like_album(album_id)
            log_status = "LIKED_MANUAL"
        else:
            log_status = "EXCLUDED_MANUAL"

        # 2. Remove tracks from playlist (for both REMOVE and PROMOTE)
        # We must fetch tracks to get their IDs
        album_object = tidal_client.session.album(album_id)
        tracks = album_object.tracks()
        
        if tracks:
            track_ids = [t.id for t in tracks]
            playlist.remove_by_id(track_ids)
            print(f"  > Removed {len(track_ids)} tracks from '{PLAYLIST_NAME}'.")
        else:
            print("  > Warning: No tracks found for album. Playlist unchanged.")

        # 3. Update Log
        update_processed_log(artist, album_title, status=log_status)
        return True
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

if __name__ == "__main__":
    print("CleanupAgent: Running in workflow mode...")
    
    artist = os.getenv("CLEANUP_ARTIST")
    album = os.getenv("CLEANUP_ALBUM")
    album_id = os.getenv("CLEANUP_ALBUM_ID")
    action = os.getenv("CLEANUP_ACTION", "REMOVE") # Default to remove

    if not all([artist, album, album_id]):
        print("Error: Missing inputs.")
        sys.exit(1)

    success = handle_album_action(artist, album, album_id, action)
    
    if not success:
        sys.exit(1)
