import json
import os
import time

# --- Configuration ---
INPUT_FILE_PATH = 'data/raw_album_list.json'
OUTPUT_FILE_PATH = 'data/filtered_album_list.json'
PROMPT_FILE_PATH = 'config/analyzer_prompt.txt'
OUTPUT_DIR = 'data'

# --- Placeholder for Google AI API Call ---
def get_ai_analysis(album_info, system_prompt):
    """
    This is a placeholder function.
    In the future, this function will make an API call to Google AI.
    It will send the system_prompt and the album_info,
    and it will return a JSON object with the analysis.
    """
    print(f"  > Analyzing: {album_info.get('artist', 'Unknown')} - {album_info.get('album', 'Unknown')}")
    # Simulate an API call delay
    time.sleep(0.5) 
    
    # --- MOCKED RESPONSE ---
    # We'll return a fake response that matches our prompt's output format
    # This lets us test the whole pipeline without real API calls.
    mock_decision = "ADD_TO_PLAYLIST"
    if "Test Album" in album_info.get('album', ''):
        mock_decision = "LIKE_IMMEDIATELY"

    return {
      "artist": album_info.get('artist', 'Unknown'),
      "album": album_info.get('album', 'Unknown'),
      "relevance_score": 85,
      "decision": mock_decision,
      "reasoning": "This is a mocked analysis. The real AI would provide a reason.",
      "key_descriptors": ["mocked", "placeholder"]
    }
    # --- END MOCKED RESPONSE ---

# --- Main Function ---
def analyze_albums():
    print("AnalysisAgent: Starting run...")
    
    # 1. Load the system prompt
    try:
        with open(PROMPT_FILE_PATH, 'r') as f:
            system_prompt = f.read()
        print("Successfully loaded AI prompt.")
    except FileNotFoundError:
        print(f"Error: Prompt file not found at {PROMPT_FILE_PATH}")
        return

    # 2. Load the raw albums list
    try:
        with open(INPUT_FILE_PATH, 'r') as f:
            raw_albums = json.load(f)
        print(f"Found {len(raw_albums)} albums to analyze.")
    except FileNotFoundError:
        print(f"Note: Raw albums file not found at {INPUT_FILE_PATH}. (This is normal on first run).")
        raw_albums = [] # Start with an empty list if file doesn't exist
    except json.JSONDecodeError:
        print(f"Error: Could not decode {INPUT_FILE_PATH}. Assuming empty.")
        raw_albums = []
        
    if not raw_albums:
        # Create a dummy album for testing if the list is empty
        # This helps us confirm the pipeline works end-to-end
        print("Creating dummy album for testing pipeline...")
        raw_albums = [{
            "artist": "Test Artist", 
            "album": "Test Album", 
            "source": "dummy_source"
        }]

    # 3. Analyze each album
    filtered_albums = []
    for album_info in raw_albums:
        # Call our placeholder AI function
        analysis_result = get_ai_analysis(album_info, system_prompt)
        
        # Only save albums that we want to take action on
        if analysis_result.get('decision') in ["ADD_TO_PLAYLIST", "LIKE_IMMEDIATELY"]:
            filtered_albums.append(analysis_result)

    # 4. Save the results
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE_PATH, 'w') as f:
        json.dump(filtered_albums, f, indent=2)
        
    print(f"\nAnalysisAgent: Run complete. Approved {len(filtered_albums)} albums.")
    print(f"Results saved to {OUTPUT_FILE_PATH}")

# --- Run the script ---
if __name__ == "__main__":
    analyze_albums()
