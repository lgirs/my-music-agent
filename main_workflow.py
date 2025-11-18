# We need to tell Python to look in the 'agents' folder
# This part is a bit of a quirk but necessary
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'agents')))

# --- Import Our Agents ---
try:
    from harvester_agent import harvest_new_albums
    from analysis_agent import analyze_albums
    from tidal_agent import take_tidal_actions
    from cleanup_agent import process_commands
except ImportError:
    print("Error: Could not import agents.")
    print("Make sure 'harvester_agent.py', 'analysis_agent.py', 'tidal_agent.py', and 'cleanup_agent.py' exist in the /agents folder.")
    sys.exit(1)

# --- Main Workflow Function ---
def run_full_workflow():
    print("==========================================")
    print("🚀 STARTING PERSONAL MUSIC AGENT WORKFLOW")
    print("==========================================")
    
    try:
        # --- STAGE 1: HARVEST ---
        print("\n--- STAGE 1: HARVESTER AGENT ---")
        harvest_new_albums()
        
        # --- STAGE 2: ANALYSIS ---
        print("\n--- STAGE 2: ANALYSIS AGENT ---")
        analyze_albums()
        
        # --- STAGE 3: TIDAL ACTION ---
        print("\n--- STAGE 3: TIDAL ACTION AGENT ---")
        take_tidal_actions()

        # --- STAGE 4: CLEANUP & COMMANDS (NEW) ---
        print("\n--- STAGE 4: CLEANUP & COMMAND AGENT ---")
        process_commands()
        
    except Exception as e:
        print(f"\n--- !! WORKFLOW FAILED !! ---")
        print(f"An error occurred: {e}")
        # In the future, this could send you an email alert
        
    print("\n==========================================")
    print("✅ WORKFLOW COMPLETE")
    print("==========================================")

# --- Run the script ---
if __name__ == "__main__":
    run_full_workflow()
