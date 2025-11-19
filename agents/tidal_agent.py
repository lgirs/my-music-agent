import json
import os
import time
import requests
from dotenv import load_dotenv
from tidalapi import Session, Quality
import tidalapi
from fuzzywuzzy import fuzz

# --- Configuration ---
INPUT_FILE_PATH = 'data/filtered_album_list.json'
HARVESTER_LOG_PATH = 'data/harvester_log.json'
PROCESSED_LOG_PATH = 'data/processed_albums.json' 
LOG_FILE_PATH = 'data/run_log.txt'
REPORT_FILE_PATH = 'data/index.html'
OUTPUT_DIR = 'data'
PLAYLIST_NAME = "AI Music Discovery"
MAX_LIKED_ALBUMS_PER_RUN = 5 
FUZZY_MATCH_THRESHOLD = 85

# --- RealTidalClient Class (No Change) ---
class RealTidalClient:
    def __init__(self):
        self.session = Session()
        # Load environment variables (TIDAL_* secrets) from .env if running locally
        load_dotenv(dotenv_path='config/.env') 
        token_type = os.getenv("TIDAL_TOKEN_TYPE")
        access_token = os.getenv("TIDAL_ACCESS_TOKEN")
        refresh_token = os.getenv("TIDAL_REFRESH_TOKEN")
        expiry_time = os.getenv("TIDAL_EXPIRY_TIME")
        if not all([token_type, access_token, refresh_token, expiry_time]):
            print("Error: Tidal auth tokens not found...")
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

    def get_playlist(self, name):
        for pl in self.session.user.playlists():
            if pl.name == name:
                return pl
        return None

    def get_current_playlist_albums_for_report(self, playlist_name):
        print(f"  > Fetching current contents of '{playlist_name}'...")
        playlist = self.get_playlist(playlist_name)
        if not playlist:
            print(f"  > Playlist '{playlist_name}' not found.")
            return []

        album_set = set()
        album_list = []
        
        try:
            tracks = playlist.tracks()
        except requests.exceptions.HTTPError as e:
            print(f"  > Error fetching playlist tracks: {e}")
            return []

        for track in tracks:
            album = track.album
            album_key = album.id
            if album_key not in album_set:
                album_set.add(album_key)
                album_list.append({
                    'artist': album.artist.name if album.artist else 'Unknown Artist',
                    'album': album.name,
                    'album_id': album.id
                })
        
        print(f"  > Found {len(album_list)} unique albums in '{playlist_name}'.")
        return album_list

    def find_album_id(self, artist, album_to_find):
        print(f"  > Searching Tidal for: '{album_to_find}' by '{artist}'...")
        try:
            search_results = self.session.search(f"{artist} {album_to_find}", models=[tidalapi.Album])
            if not search_results or not search_results['albums']:
                return {"id": None, "status": "NOT_FOUND", "title": album_to_find, "score": 0}
            best_match = None
            highest_score = 0
            for tidal_album in search_results['albums'][:5]:
                score = fuzz.token_sort_ratio(album_to_find, tidal_album.name)
                if tidal_album.artist.name.lower() == artist.lower():
                    score += 10
                if score > highest_score:
                    highest_score = score
                    best_match = tidal_album
            if highest_score > FUZZY_MATCH_THRESHOLD:
                return {
                    "id": best_match.id,
                    "status": "FUZZY_MATCH" if highest_score < 98 else "EXACT_MATCH",
                    "title": best_match.name,
                    "score": highest_score
                }
            return {"id": None, "status": "NOT_FOUND", "title": album_to_find, "score": 0}
        except Exception as e:
            print(f"  > Error searching for album: {e}")
            return {"id": None, "status": "ERROR", "title": str(e), "score": 0}

    def like_album(self, album_id, artist, album):
        print(f"  > ACTION: 'Liking' album (ID: {album_id}) - '{album}' by '{artist}'")
        self.session.user.favorites.add_album(album_id)

    def add_album_to_playlist(self, album_id, artist, album, playlist_name):
        print(f"  > ACTION: Adding to playlist '{playlist_name}' (ID: {album_id}) - '{album}' by '{artist}'")
        album_object = self.session.album(album_id)
        tracks = album_object.tracks()
        track_ids = [track.id for track in tracks]
        
        playlist = self.get_playlist(playlist_name)
        if not playlist:
            print(f"  > Playlist '{playlist_name}' not found. Creating it...")
            new_pl = self.session.user.create_playlist(playlist_name, "Created by my AI agent.")
            playlist = new_pl

        playlist.add(track_ids)
        print(f"  > Successfully added {len(track_ids)} tracks to '{playlist_name}'.")

# --- Helper for Log Management (No Change) ---
def load_processed_albums():
    try:
        with open(PROCESSED_LOG_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_processed_album(album_data):
    processed_albums = load_processed_albums()
    unique_key = f"{album_data['artist']}::{album_data['album']}"
    if not any(item['key'] == unique_key for item in processed_albums):
        processed_albums.append({
            "key": unique_key,
            "artist": album_data['artist'],
            "album": album_data['album'],
            "timestamp": time.time(),
            "action": album_data.get('decision')
        })
        with open(PROCESSED_LOG_PATH, 'w') as f:
            json.dump(processed_albums, f, indent=2)
    
# --- process_album_action (No Change) ---
def process_album_action(tidal_client, album_data):
    artist = album_data.get('artist', 'Unknown')
    album_to_find = album_data.get('album', 'Unknown')
    decision = album_data.get('decision')
    ai_score = album_data.get('relevance_score', 0)
    reasoning = album_data.get('reasoning', 'N/A')

    if not artist or not album_to_find:
        return ("SKIPPED_INVALID", artist, f"Invalid data: {album_data}", "", ai_score, reasoning)

    match_info = tidal_client.find_album_id(artist, album_to_find)
    
    if match_info["status"] == "NOT_FOUND":
        return ("NOT_FOUND", artist, album_to_find, "", ai_score, reasoning)
    if match_info["status"] == "ERROR":
        return ("ERROR", artist, album_to_find, match_info['title'], ai_score, reasoning)

    album_id = match_info["id"]
    found_title = match_info["title"]
    match_status = match_info["status"]
    
    try:
        if decision == "LIKE_IMMEDIATELY":
            tidal_client.like_album(album_id, artist, found_title)
            return ("LIKED_" + match_status, artist, album_to_find, found_title, ai_score, reasoning)
        elif decision == "ADD_TO_PLAYLIST":
            tidal_client.add_album_to_playlist(album_id, artist, found_title, playlist_name=PLAYLIST_NAME)
            return ("ADDED_" + match_status, artist, album_to_find, found_title, album_data['relevance_score'], reasoning)
    except Exception as e:
        print(f"  > Error during Tidal action: {e}")
        return ("ERROR", artist, album_to_find, str(e), ai_score, reasoning)
    
    return ("UNKNOWN", artist, album_to_find, "", ai_score, reasoning)


# --- generate_html_report (No Change, but good to refresh) ---
def generate_html_report(actions_list, processed_log_len, current_playlist_albums):
    print(f"  > Generating HTML report...")

    try:
        with open(HARVESTER_LOG_PATH, 'r') as f:
            harvester_log = json.load(f)
    except Exception:
        harvester_log = []

    def format_li(status, artist, original, found, score, reasoning):
        artist = artist.replace('<', '&lt;').replace('>', '&gt;')
        original = original.replace('<', '&lt;').replace('>', '&gt;')
        found = found.replace('<', '&lt;').replace('>', '&gt;')
        reasoning = reasoning.replace('<', '&lt;').replace('>', '&gt;')

        score_html = f"<span class='score'>[AI Score: {score}]</span>"
        reason_html = f"<br><span class='reasoning'>&nbsp;&nbsp;↳ <i>AI Reason: {reasoning}</i></span>"
        
        if not found:
            return f"<li><b>{artist} - {original}</b> {score_html}{reason_html}</li>" 
        
        if "FUZZY" in status:
            return f"<li><b>{artist} - {original}</b> {score_html}<br><span class='fuzzy'>&nbsp;&nbsp;↳ Matched as: <i>{found}</i></span>{reason_html}</li>"
        
        return f"<li><b>{artist} - {found}</b> {score_html}{reason_html}</li>"

    # --- MODIFIED BUTTON GENERATOR ---
    def format_current_album_li(album_data):
        artist_safe = album_data['artist'].replace('<', '&lt;').replace('>', '&gt;')
        album_safe = album_data['album'].replace('<', '&lt;').replace('>', '&gt;')
        album_id = album_data['album_id']
        
        # We need a form to submit the data required by the cleanup_agent
        # *** REMEMBER TO REPLACE OWNER/REPO WITH YOUR ACTUAL PATH ***
        remove_form = f"""
            <form style="display:inline;" action="https://github.com/lgirs/my-music-agent/actions/workflows/cleanup_trigger.yml" method="post" target="_blank">
                <input type="hidden" name="ref" value="main">
                <input type="hidden" name="inputs" value='{{"artist": "{artist_safe}", "album": "{album_safe}", "album_id": "{album_id}", "action_type": "REMOVE"}}'>
                <button type="submit" class="remove-btn">Remove Album</button>
            </form>
        """
        
        # --- PROMOTION BUTTON ADDED HERE ---
        promote_form = f"""
            <form style="display:inline; margin-right: 10px;" action="https://github.com/lgirs/my-music-agent/actions/workflows/cleanup_trigger.yml" method="post" target="_blank">
                <input type="hidden" name="ref" value="main">
                <input type="hidden" name="inputs" value='{{"artist": "{artist_safe}", "album": "{album_safe}", "album_id": "{album_id}", "action_type": "PROMOTE"}}'>
                <button type="submit" class="promote-btn">Promote to Liked</button>
            </form>
        """
        
        return f"""
        <li style="position: relative;">
            <b>{artist_safe} - {album_safe}</b>
            <div style="float:right;">
                {promote_form}
                {remove_form}
            </div>
        </li>
        """
    
    # --- ISOLATED JAVASCRIPT STRING (FIXES SYNTAX ERROR) ---
    js_script = """
            document.querySelectorAll('form').forEach(form => {
                form.addEventListener('submit', function(e) {
                    const inputs = this.querySelector('input[name="inputs"]').value;
                    let data;
                    let action = this.querySelector('button').innerText.includes("Remove") ? "remove" : "promote";

                    try {
                        data = JSON.parse(inputs);
                    } catch (error) {
                        console.error("Failed to parse JSON inputs:", error);
                        alert("Error: Could not process removal data.");
                        e.preventDefault();
                        return;
                    }

                    let message;
                    if (action === "remove") {
                        message = `Are you sure you want to permanently REMOVE and EXCLUDE the album "${data.album}" by ${data.artist}?`;
                    } else {
                        message = `Are you sure you want to PROMOTE the album "${data.album}" by ${data.artist} to your Liked Albums? (This will also remove it from the playlist).`;
                    }
                    
                    const isConfirmed = confirm(message);
                    
                    if (!isConfirmed) {
                        e.preventDefault();
                    } else {
                        alert(`Request submitted for "${data.album}". Check the GitHub Actions page for status.`);
                    }
                });
            });
    """

    liked_exact = [format_li(*a) for a in actions_list if a[0] == "LIKED_EXACT_MATCH"]
    liked_fuzzy = [format_li(*a) for a in actions_list if a[0] == "LIKED_FUZZY_MATCH"]
    added_exact = [format_li(*a) for a in actions_list if a[0] == "ADDED_EXACT_MATCH"]
    added_fuzzy = [format_li(*a) for a in actions_list if a[0] == "ADDED_FUZZY_MATCH"]
    not_found = [format_li(*a) for a in actions_list if a[0] == "NOT_FOUND"]
    errors = [format_li(*a) for a in actions_list if a[0] == "ERROR"]
    skipped_dupe = [format_li(*a) for a in actions_list if a[0].startswith("SKIPPED_PROCESSED")]

    current_playlist_html = ''.join([format_current_album_li(a) for a in current_playlist_albums])

    harvester_errors = [l for l in harvester_log if l['status'] == 'error']
    harvester_success = [l for l in harvester_log if l['status'] == 'success']

    harvester_error_html = ''.join([f"<li><b>{h['source']}</b><br><span class='fuzzy'>&nbsp;&nbsp;↳ {h['message']}</span></li>" for h in harvester_errors])
    harvester_success_html = ''.join([f"<li><b>{h['source']}</b><br>&nbsp;&nbsp;↳ {h['message']}</li>" for h in harvester_success])

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Music Agent Report</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: auto; background-color: #f6f8fa; }}
            h1, h2 {{ border-bottom: 2px solid #eaecef; padding-bottom: 10px; }}
            h1 {{ font-size: 32px; }}
            h2 {{ font-size: 24px; margin-top: 40px; }}
            ul {{ list-style-type: none; padding-left: 0; }}
            li {{ background-color: #ffffff; border: 1px solid #d1d5da; padding: 12px; margin-bottom: 8px; border-radius: 6px; position: relative; }}
            .score {{ float: right; color: #586069; font-size: 0.9em; font-weight: bold; }}
            .fuzzy {{ color: #b08800; font-size: 0.9em; }}
            .reasoning {{ color: #586069; font-size: 0.9em; }}
            .error li {{ background-color: #fff8f8; border-color: #d73a49; }}
            .not-found li {{ background-color: #fffbf0; border-color: #f0ad4e; }}
            .skipped li {{ background-color: #e6f7ff; border-color: #1890ff; }}
            .remove-btn {{ float: right; background-color:#d73a49; color:white; border:none; padding: 5px 10px; border-radius:3px; cursor:pointer; }}
            .promote-btn {{ float: right; background-color:#1890ff; color:white; border:none; padding: 5px 10px; border-radius:3px; cursor:pointer; margin-right: 10px; }}
        </style>
    </head>
    <body>
        <h1>🎵 Music Agent Report</h1>
        <p>Last run: {time.ctime()} | Albums tracked in history: {processed_log_len}</p>

        <h2 class="error">🌐 Source Harvester Errors ({len(harvester_errors)})</h2>
        <p>These sites failed to load. We need to fix the URLs or remove them from <code>sources.json</code>.</p>
        <ul>
            {harvester_error_html or "<li>None</li>"}
        </ul>
        
        <h2>🗑️ Current 'AI Music Discovery' Contents ({len(current_playlist_albums)})</h2>
        <p>Use the buttons to manage your playlist. The dashboard will copy the data to your clipboard and open the GitHub Actions page.</p>
        <ul>
            {current_playlist_html or "<li>The 'AI Music Discovery' playlist is currently empty or could not be accessed.</li>"}
        </ul>

        <h2 class="skipped">🚫 Skipped Duplicates ({len(skipped_dupe)})</h2>
        <p>These albums were successfully filtered against the permanent history file (<code>processed_albums.json</code>).</p>
        <ul>
            { "".join(skipped_dupe) or "<li>None</li>"}
        </ul>

        <h2 class="not-found">❗ Action Required: Not Found ({len(not_found)})</h2>
        <p>These albums passed the AI filter but could not be found on Tidal.</p>
        <ul>
            { "".join(not_found) or "<li>None</li>"}
        </ul>

        <h2 class="error">❌ Tidal API Errors ({len(errors)})</h2>
        <p>These albums were found, but a system error occurred during the Tidal action.</p>
        <ul>
            { "".join(errors) or "<li>None</li>"}
        </ul>

        <h2>⭐ Albums Liked ({len(liked_exact) + len(liked_fuzzy)})</h2>
        <p>These are the Top {MAX_LIKED_ALBUMS_PER_RUN} albums with the highest AI scores.</p>
        <ul>
            { "".join(liked_exact)}
            { "".join(liked_fuzzy)}
            {'<li>None</li>' if not (liked_exact or liked_fuzzy) else ''}
        </ul>

        <h2>🎶 Added to 'AI Music Discovery' ({len(added_exact) + len(added_fuzzy)})</h2>
        <p>These albums were also recommended by the AI and added to your playlist.</p>
        <ul>
            { "".join(added_exact)}
            { "".join(added_fuzzy)}
            {'<li>None</li>' if not (added_exact or added_fuzzy) else ''}
        </ul>

        <h2>✅ Source Harvester Success ({len(harvester_success)})</h2>
        <p>These sites were successfully scanned for content.</p>
        <ul>
            {harvester_success_html or "<li>None</li>"}
        </ul>
        
        <script>
            {js_script}
        </script>
    </body>
    </html>
    """
    
    try:
        with open(REPORT_FILE_PATH, 'w') as f:
            f.write(html)
        print(f"  > Successfully wrote HTML report to {REPORT_FILE_PATH}")
    except Exception as e:
        print(f"  > Error writing HTML report: {e}")


# --- Main Function (Modified) ---
def take_tidal_actions():
    print("TidalActionAgent: Starting run...")
    
    # --- Load Processed Log ---
    processed_albums_keys = {f"{item['artist']}::{item['album']}" for item in load_processed_albums()}
    
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
        print(f"Note: Filtered albums file not found or empty. No albums processed.")
        filtered_albums = []
        
    # --- Anti-Duplication Filter ---
    albums_to_process = []
    albums_skipped = []

    for album in filtered_albums:
        unique_key = f"{album.get('artist')}::{album.get('album')}"
        if unique_key in processed_albums_keys:
            album_data_tuple = ("SKIPPED_PROCESSED", album.get('artist'), album.get('album'), "N/A", album.get('relevance_score'), "Skipped: Already processed in a previous run.")
            albums_skipped.append(album_data_tuple)
        else:
            albums_to_process.append(album)
            
    if albums_skipped:
        print(f"  > Skipped {len(albums_skipped)} albums already found in history.")

    # --- Separate and Cap the filtered list ---
    albums_to_like_raw = [a for a in albums_to_process if a.get('decision') == 'LIKE_IMMEDIATELY']
    albums_to_playlist = [a for a in albums_to_process if a.get('decision') == 'ADD_TO_PLAYLIST']
    albums_to_like_raw.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    # Apply the capping rule
    albums_to_like = albums_to_like_raw[:MAX_LIKED_ALBUMS_PER_RUN]
    
    print(f"  > Found {len(albums_to_like)} albums to 'Like' and {len(albums_to_playlist)} to 'Add to Playlist'.")

    actions_list_for_report = [] 
    actions_list_for_report.extend(albums_skipped) # Add skipped list to report

    # --- Process Actions ---
    print(f"\n--- Processing {len(albums_to_like)} 'Like' Actions ---")
    for album_data in albums_to_like:
        action_result_tuple = process_album_action(tidal_client, album_data)
        actions_list_for_report.append(action_result_tuple)
        # Log successful action
        if action_result_tuple[0].startswith("LIKED"):
            save_processed_album(album_data)

    print(f"\n--- Processing {len(albums_to_playlist)} 'Playlist' Actions ---")
    for album_data in albums_to_playlist:
        action_result_tuple = process_album_action(tidal_client, album_data)
        actions_list_for_report.append(action_result_tuple)
        # Log successful action
        if action_result_tuple[0].startswith("ADDED"):
            save_processed_album(album_data)
    
    # --- MOVED TO END: Fetch Current Playlist Albums for Report (AFTER processing) ---
    current_playlist_albums = tidal_client.get_current_playlist_albums_for_report(PLAYLIST_NAME)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(LOG_FILE_PATH, 'a') as f:
        f.write(f"\n--- TidalAgent Run: {time.ctime()} ---\n")
        for status, artist, original, found, score, reasoning in actions_list_for_report:
            f.write(f"[{status}] (Score: {score}) | Artist: '{artist}' | Looking for: '{original}' | Found: '{found}' | Reason: {reasoning}\n")
    
    generate_html_report(actions_list_for_report, len(load_processed_albums()), current_playlist_albums)
    
    print(f"\nTidalActionAgent: Run complete. Processed {len(actions_list_for_report)} total actions.")
    print(f"Actions logged to {LOG_FILE_PATH} and {REPORT_FILE_PATH}")

if __name__ == "__main__":
    take_tidal_actions()
