import json
import os
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
PROMPT_FILE_PATH = 'config/discovery_prompt.txt'
SOURCES_FILE_PATH = 'config/sources.json'
OUTPUT_FILE_PATH = 'data/suggested_sources.json' # We'll output a suggestion file
OUTPUT_DIR = 'data'

# --- Load API Key and Configure AI ---
load_dotenv(dotenv_path='config/.env')
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("Error: GOOGLE_API_KEY not found. Make sure it's set in your GitHub Secrets.")
else:
    genai.configure(api_key=API_KEY)

def run_discovery():
    print("SourceDiscoveryAgent: Starting run...")

    # 1. Load the discovery prompt
    try:
        with open(PROMPT_FILE_PATH, 'r') as f:
            system_prompt = f.read()
        print("Successfully loaded discovery prompt.")
    except FileNotFoundError:
        print(f"Error: Prompt file not found at {PROMPT_FILE_PATH}")
        return

    # 2. Load the CURRENT sources (to pass to the AI)
    try:
        with open(SOURCES_FILE_PATH, 'r') as f:
            current_sources = json.load(f)
        user_content = f"Here is my current list of sources. Please find new ones based on my prompt.\n\n{json.dumps(current_sources, indent=2)}"
    except FileNotFoundError:
        print(f"Warning: {SOURCES_FILE_PATH} not found. Running with no current sources.")
        user_content = "I have no current sources. Please find new ones based on my prompt."

    # 3. Call the AI to get new sources
    print("  > [AI] Calling Gemini to find new sources...")
    try:
        model = genai.GenerativeModel(
            'gemini-2.5-flash',
            system_instruction=system_prompt
        )
        response = model.generate_content(user_content)
        
        # The AI should be prompted to return a JSON list
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        suggested_sources = json.loads(json_text)
        print(f"  > [AI] Found {len(suggested_sources)} new potential sources.")

    except Exception as e:
        print(f"  > [AI Error] An error occurred: {e}")
        suggested_sources = []

    # 4. Save the suggestions
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE_PATH, 'w') as f:
        json.dump(suggested_sources, f, indent=2)
        
    print(f"\nSourceDiscoveryAgent: Run complete. Suggestions saved to {OUTPUT_FILE_PATH}")

if __name__ == "__main__":
    run_discovery()
