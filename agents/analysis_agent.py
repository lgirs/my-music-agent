import json
import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
INPUT_FILE_PATH = 'data/raw_album_list.json'
OUTPUT_FILE_PATH = 'data/filtered_album_list.json'
PROMPT_FILE_PATH = 'config/analyzer_prompt.txt'
OUTPUT_DIR = 'data'

# --- Load API Key and Configure AI ---
# This loads the GOOGLE_API_KEY from your config/.env file
load_dotenv(dotenv_path='config/.env')
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("Error: GOOGLE_API_KEY not found. Make sure it's set in a .env file in the config/ directory.")
else:
    genai.configure(api_key=API_KEY)

# --- REAL Google AI API Call ---
def get_ai_analysis(album_info, system_prompt):
    """
    This function makes a REAL API call to Google AI
    to analyze the album.
    """
    print(f"  > [AI] Analyzing: {album_info.get('artist', 'Unknown')} - {album_info.get('album', 'Unknown')}")
    
    try:
        # Initialize the model with your system prompt
        model = genai.GenerativeModel(
            'gemini-pro', # You can update this to newer models
            system_instruction=system_prompt
        )
        
        # Format the album info as the "user" message
        user_content = (
            "Please analyze this album based on the review I found:\n"
            f"ARTIST: {album_info.get('artist')}\n"
            f"ALBUM: {album_info.get('album')}\n"
            f"SOURCE: {album_info.get('source')}\n\n"
            "Provide your JSON analysis."
        )

        # Generate the content
        response = model.generate_content(user_content)
        
        # Clean the response and parse the JSON
        # The AI often wraps JSON in ```json ... ```
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        
        analysis_json = json.loads(json_text)
        return analysis_json

    except json.JSONDecodeError:
        print(f"  > [AI Error] Failed to decode JSON from AI response: {response.text}")
        return None # Return None to skip this album
    except Exception as e:
        print(f"  > [AI Error] An error occurred: {e}")
        return None # Return None to skip this album

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
        print(f"Note: Raw albums file not found at {INPUT_FILE_PATH}. No albums to process.")
        raw_albums = []
    except json.JSONDecodeError:
        print(f"Error: Could not decode {INPUT_FILE_PATH}. Assuming empty.")
        raw_albums = []
        
    if not raw_albums:
        print("No raw albums found. Exiting analysis.")
        # We no longer create a dummy album
        
    # 3. Analyze each album
    filtered_albums = []
    for album_info in raw_albums:
        # Call our REAL AI function
        analysis_result = get_ai_analysis(album_info, system_prompt)
        
        # Check if the result is valid AND passes our criteria
        if analysis_result and analysis_result.get('decision') in ["ADD_TO_PLAYLIST", "LIKE_IMMEDIATELY"]:
            filtered_albums.append(analysis_result)
        else:
            print(f"  > [AI] Decision: IGNORE or FAILED. Skipping album.")

    # 4. Save the results
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE_PATH, 'w') as f:
        json.dump(filtered_albums, f, indent=2)
        
    print(f"\nAnalysisAgent: Run complete. Approved {len(filtered_albums)} albums.")
    print(f"Results saved to {OUTPUT_FILE_PATH}")

# --- Run the script ---
if __name__ == "__main__":
    analyze_albums()
