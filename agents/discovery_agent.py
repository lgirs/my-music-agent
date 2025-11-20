import json
import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
PROMPT_FILE_PATH = 'config/discovery_prompt.txt'
SOURCES_FILE_PATH = 'config/sources.json'
REPORT_FILE_PATH = 'data/discovery_report.html'
OUTPUT_DIR = 'data'

# --- Load API Key and Configure AI ---
load_dotenv(dotenv_path='config/.env')
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    print("Error: GOOGLE_API_KEY not found. Make sure it's set in your GitHub Secrets.")
else:
    genai.configure(api_key=API_KEY)

def generate_discovery_report(added, removed, current_sources):
    print(f"  > Generating Discovery HTML report...")
    
    added_html = "".join([f"<li style='color:green;'><b>+ ADDED:</b> {s['Source_Name']} ({s.get('Primary_Genre_Focus', 'N/A')})</li>" for s in added])
    removed_html = "".join([f"<li style='color:red;'><b>- REMOVED:</b> {s['website']}</li>" for s in removed])
    
    if not added: added_html = "<li>No new sources added.</li>"
    if not removed: removed_html = "<li>No sources removed.</li>"

    current_rows = ""
    for s in current_sources:
        # Handle key mismatch between config (website) and AI output (Source_Name)
        name = s.get('Source_Name') or s.get('website')
        genre = s.get('Primary_Genre_Focus') or s.get('genre_focus')
        tier = s.get('Tier') or s.get('category', 'N/A')
        
        current_rows += f"<tr><td>{name}</td><td>{genre}</td><td>{tier}</td></tr>"

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Discovery Agent Report</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; max-width: 800px; margin: auto; background: #f4f4f9; }}
            h1, h2 {{ border-bottom: 1px solid #ccc; padding-bottom: 10px; }}
            ul {{ background: #fff; padding: 20px; border-radius: 8px; list-style: none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            li {{ padding: 5px 0; border-bottom: 1px solid #eee; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: #fff; }}
            th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #007bff; color: white; }}
        </style>
    </head>
    <body>
        <h1>🕵️ Discovery Agent Report</h1>
        <p>Run Date: {time.ctime()}</p>
        
        <h2>Changes Made</h2>
        <ul>
            {added_html}
            {removed_html}
        </ul>

        <h2>Current Source List ({len(current_sources)})</h2>
        <table>
            <tr><th>Source Name</th><th>Focus</th><th>Tier</th></tr>
            {current_rows}
        </table>
    </body>
    </html>
    """
    
    with open(REPORT_FILE_PATH, 'w') as f:
        f.write(html)
    print(f"  > Report saved to {REPORT_FILE_PATH}")

def run_discovery():
    print("SourceDiscoveryAgent: Starting run...")

    # 1. Load Resources
    try:
        with open(PROMPT_FILE_PATH, 'r') as f:
            system_prompt = f.read()
        with open(SOURCES_FILE_PATH, 'r') as f:
            current_config = json.load(f)
            current_sources_list = current_config.get('sources', [])
    except FileNotFoundError as e:
        print(f"Error: File not found: {e}")
        return

    # 2. Prepare AI Context
    # We map the existing config to the format the AI expects to minimize hallucination
    context_sources = []
    for s in current_sources_list:
        context_sources.append({
            "Source_Name": s.get('website'),
            "URL": s.get('url'),
            "Tier": s.get('category'),
            "Primary_Genre_Focus": s.get('genre_focus'),
            # Include other fields if necessary to match prompt schema
        })
        
    user_content = f"Here is my current list of sources. Please audit them and output the updated JSON list of 30 sources.\n\n{json.dumps(context_sources, indent=2)}"

    # 3. Call AI
    print("  > [AI] Calling Gemini to audit and curate sources...")
    try:
        model = genai.GenerativeModel(
            'gemini-2.5-flash',
            system_instruction=system_prompt
        )
        response = model.generate_content(user_content)
        
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        new_sources_list = json.loads(json_text)
        print(f"  > [AI] Returned {len(new_sources_list)} sources.")

    except Exception as e:
        print(f"  > [AI Error] An error occurred: {e}")
        return

    # 4. Diff & Update Logic
    # Create sets of names for easy comparison
    old_names = {s['website'] for s in current_sources_list}
    new_names = {s['Source_Name'] for s in new_sources_list}
    
    added_sources = [s for s in new_sources_list if s['Source_Name'] not in old_names]
    removed_sources = [s for s in current_sources_list if s['website'] not in new_names]

    print(f"  > Analysis: {len(added_sources)} new added, {len(removed_sources)} removed.")

    # 5. Transformation: Convert AI Output format back to Config format
    # The AI returns keys like "Source_Name", but your harvester needs "website", "url", "category".
    final_config_list = []
    for s in new_sources_list:
        final_config_list.append({
            "category": s.get('Tier', 'Uncategorized'),
            "website": s.get('Source_Name'),
            "relevancy_score": s.get('Relevancy_Score', 5.0),
            "genre_focus": s.get('Primary_Genre_Focus', 'General'),
            "description": s.get('Key_Critical_Strength', ''),
            "url": s.get('URL')
        })

    # 6. Save Updates
    final_config = {"sources": final_config_list}
    
    with open(SOURCES_FILE_PATH, 'w') as f:
        json.dump(final_config, f, indent=2)
    print(f"  > Overwrote {SOURCES_FILE_PATH} with new source list.")

    # 7. Generate Report
    generate_discovery_report(added_sources, removed_sources, final_config_list)
    
    print("\nSourceDiscoveryAgent: Run complete.")

if __name__ == "__main__":
    run_discovery()
