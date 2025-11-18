import json
import os
import time
from dotenv import load_dotenv
from tidalapi import Session, UserPlaylist

# --- Configuration ---
DISCOVERY_PLAYLIST = "Weekly Discovery"
REMOVE_CMD_PLAYLIST = "[Agent] Remove"
PROMOTE_CMD_PLAYLIST = "[Agent] Promote"
PROCESSED_LOG_PATH = 'data/processed_albums.json'

# --- Tidal Client ---
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
            print(f"CleanupAgent: Authenticated as {self.user.username}")
        except Exception as e:
            print(f"Failed to authenticate: {e}")
            raise

    def get_or_create_playlist(self, name, description=""):
        """Finds a playlist or creates it if missing."""
        for pl in self.session.user.playlists():
            if pl.name == name:
                return pl
        
        print(f"  > Playlist '{name}' not found. Creating it...")
        return self.session.user.create_playlist(name, description)

# --- Log Management ---
def update_processed_log(artist, album, status):
    try:
        with open(PROCESSED_LOG_PATH, 'r') as f:
            processed_albums = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        processed_albums = []

    unique_key = f"{artist}::{album}"
    
    # Check if entry exists
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
    print(f"  > Log updated: '{album}' -> {status}")

# --- Core Logic ---
def process_commands():
    print("CleanupAgent: Checking for commands in Tidal playlists...")
    
    try:
        client = RealTidalClient()
    except Exception:
        return

    # 1. Get all necessary playlists
    discovery_pl = client.get_or_create_playlist(DISCOVERY_PLAYLIST)
    remove_pl = client.get_or_create_playlist(REMOVE_CMD_PLAYLIST, "Add tracks here to remove their album from Discovery.")
    promote_pl = client.get_or_create_playlist(PROMOTE_CMD_PLAYLIST, "Add tracks here to Like the album and remove from Discovery.")
    
    # 2. Process "REMOVE" Commands
    process_queue(client, remove_pl, discovery_pl, action="REMOVE")
    
    # 3. Process "PROMOTE" Commands
    process_queue(client, promote_pl, discovery_pl, action="PROMOTE")

    print("CleanupAgent: All commands processed.")

def process_queue(client, command_pl, target_pl, action):
    """Reads a command playlist, performs actions, clears command playlist."""
    tracks = command_pl.tracks()
    
    if not tracks:
        print(f"  > No commands in '{command_pl.name}'.")
        return

    print(f"\n--- Processing {len(tracks)} items in '{command_pl.name}' ---")
    
    items_to_remove_from_target = []
    processed_albums = set()

    for item in tracks:
        # Tidal playlists can contain videos/tracks. We assume tracks.
        try:
            album = item.album
            artist_name = album.artist.name if album.artist else "Unknown"
            album_title = album.name
            album_id = album.id
            
            # Avoid processing the same album twice if user added multiple songs
            if album_id in processed_albums:
                continue
            processed_albums.add(album_id)

            print(f"  > Processing: '{album_title}' by '{artist_name}'")

            # ACTION: PROMOTE (Like the album)
            if action == "PROMOTE":
                print(f"    - Liking album on Tidal...")
                client.session.user.favorites.add_album(album_id)
                log_status = "LIKED_VIA_PLAYLIST"
            else:
                log_status = "EXCLUDED_VIA_PLAYLIST"

            # ACTION: Identify tracks to remove from Target (Weekly Discovery)
            # We scan the target playlist for ANY track belonging to this album
            target_tracks = target_pl.tracks()
            for t in target_tracks:
                if t.album.id == album_id:
                    items_to_remove_from_target.append(t.id)
            
            # ACTION: Update Log
            update_processed_log(artist_name, album_title, log_status)
            
        except Exception as e:
            print(f"    - Error processing item: {e}")

    # Batch remove from Target Playlist
    if items_to_remove_from_target:
        print(f"  > Removing {len(items_to_remove_from_target)} tracks from '{target_pl.name}'...")
        # Remove duplicates just in case
        unique_ids = list(set(items_to_remove_from_target))
        target_pl.remove_by_id(unique_ids)
    else:
        print(f"  > No matching tracks found in '{target_pl.name}' to remove.")

    # FINAL STEP: Clear the Command Playlist
    # There isn't a "clear()" method, so we remove all items we just found
    cmd_item_ids = [t.id for t in tracks]
    if cmd_item_ids:
        print(f"  > Clearing command playlist '{command_pl.name}'...")
        command_pl.remove_by_id(cmd_item_ids)

if __name__ == "__main__":
    process_commands()
