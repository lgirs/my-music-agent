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
load_dotenv(dotenv_path='config/.env')
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("Error: GOOGLE_API_KEY not found. Make sure it's set in your GitHub Secrets.")
else:
    genai.configure(api_key=API_KEY)

# --- REAL Google AI API Call ---
def get_ai_analysis(page_text, source_name, system_prompt):
    """
    This function sends the ENTIRE page text to the AI for
    finding AND analyzing albums.
    """
    print(f"  > [AI] Analyzing page: {source_name} ({len(page_text)} chars)")
    
    # Truncate text if it's too long for the model's context window
    # A safe limit for gemini-pro is ~30k, but let's be safer for the prompt
    max_chars = 25000 
    if len(page_text) > max_chars:
        print(f"  > [AI] Page text is too long. Truncating to {max_chars} chars.")
        page_text = page_text[:max_chars]

    try:
        model = genai.GenerativeModel(
            'gemini-2.5-flash',
            system_instruction=system_prompt,
            # Set a higher safety threshold if needed, or keep default
            # safety_settings={'HARASSMENT': 'BLOCK_NONE'} 
        )
        
        response = model.generate_content(page_text)
        
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        
        analysis_list = json.loads(json_text)
        return analysis_list

    except json.JSONDecodeError:
        print(f"  > [AI Error] Failed to decode JSON list from AI response: {response.text}")
        return []
    except Exception as e:
        print(f"  > [AI Error] An error occurred: {e}")
        return []

# --- Main Function ---
def analyze_albums():
    print("AnalysisAgent: Starting run (AI-Parser Mode)...")
    
    try:
        with open(PROMPT_FILE_PATH, 'r') as f:
            system_prompt = f.read()
        print("Successfully loaded AI prompt.")
    except FileNotFoundError:
        print(f"Error: Prompt file not found at {PROMPT_FILE_PATH}")
        return

    try:
        with open(INPUT_FILE_PATH, 'r') as f:
            raw_pages = json.load(f)
        print(f"Found {len(raw_pages)} pages to analyze.")
    except (FileNotFoundError, json.JSONDecodeError):
        print("Note: Raw pages file not found or empty. No pages to process.")
        raw_pages = []
        
    if not raw_pages:
        print("No raw pages found. Exiting analysis.")
        
    all_approved_albums = []
    for page in raw_pages:
        if not page.get('page_text'):
            print(f"  > Skipping {page['source_name']}, no text found.")
            continue

        approved_albums_from_page = get_ai_analysis(
            page['page_text'], 
            page['source_name'], 
            system_prompt
        )
        
        if approved_albums_from_page:
            print(f"  > [AI] Found {len(approved_albums_from_page)} approved albums on {page['source_name']}.")
            all_approved_albums.extend(approved_albums_from_page)
        else:
            print(f"  > [AI] Found no relevant albums on {page['source_name']}.")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE_PATH, 'w') as f:
        json.dump(all_approved_albums, f, indent=2)
        
    print(f"\nAnalysisAgent: Run complete. Approved {len(all_approved_albums)} total albums.")
    print(f"Results saved to {OUTPUT_FILE_PATH}")

if __name__ == "__main__":
    analyze_albums()
