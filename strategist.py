import sqlite3
import json
import os
import time
from datetime import datetime, timedelta
import google.generativeai as genai
from plyer import notification
from dotenv import load_dotenv

from blocker import block_for_duration

# --- CONFIGURATION ---
load_dotenv()
DB_PATH = 'database/activity_log_gemini.db'
CHAT_HISTORY_DIR = 'chat_history'
API_KEY = os.getenv('GENAI_API_KEY_3')
ACTIVITY_DATA_DIR = 'activity_data'


# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are Janus, an AI accountability coach. Your purpose is to help the user stay focused and productive.

You will receive a summary of the user's computer activity in a JSON format. Your task is to analyze this data and respond ONLY with a valid JSON object.

The JSON object must have two keys: "comment" and "execute_code".

Use the "execute_code" to categorize the user's status based on the following rules:
- "execute_code": 1 -> The user is being highly productive and deserves praise. The "comment" should be a short, encouraging message.
- "execute_code": 0 -> The user is distracted or has lost focus. The "comment" should be a firm but helpful nudge to get them back on track.
- "execute_code": -1 -> The user's activity is neutral, balanced, or there is not enough data. No action is needed. The "comment" should be an empty string.
- "execute_code": 2 -> The user is spending time on distracting websites or applications. The "comment" should be a dictionary with keys "distracting_sites" (a list of distracting sites) and "duration" (the duration to block them for, in seconds).

Note: Don;t use execution code 2: it is under development and may not work as expected.

tools:
1. `block_for_duration(duration: int, distracting_sites: list)`: Blocks the specified distracting sites for the given duration in seconds. Example: `block_for_duration(600, ["youtube.com", "facebook.com"])` will block YouTube and Facebook for 10 minutes.

Do not use any other codes. Analyze the following user data and provide your JSON response without any additional text or formatting.
"""
# --- Tools ---



# --- HELPER FUNCTIONS ---

def setup_environment():
    """Ensure API key is set and chat history directory exists."""
    if not API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)
    genai.configure(api_key=API_KEY)

def get_chat_history_path():
    """Returns the path for today's chat history file."""
    today_str = datetime.now().strftime('%Y-%m-%d')
    return os.path.join(CHAT_HISTORY_DIR, f'chat_history_{today_str}.json')

def load_chat_session(SYSTEM_PROMPT):
    """Loads today's chat history or starts a new session."""
    history_path = get_chat_history_path()
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        system_instruction=SYSTEM_PROMPT
    )
    
    if os.path.exists(history_path):
        print(f"Loading chat history from {history_path}")
        with open(history_path, 'r') as f:
            history_data = json.load(f)
        # Recreate the ChatSession from the loaded history
        chat = model.start_chat(history=history_data)
    else:
        print("No history found for today. Starting a new chat session.")
        chat = model.start_chat()
    return chat

def save_chat_history(chat):
    """Saves the current chat session history to today's file."""
    history_path = get_chat_history_path()
    history_data = []
    for message in chat.history:
        history_data.append({
            "role": message.role,
            "parts": [part.text for part in message.parts]
        })
    
    with open(history_path, 'w') as f:
        json.dump(history_data, f, indent=2)
    print(f"Chat history saved to {history_path}")

def get_recent_activity_data():
    """Queries the DB for the last 15 minutes of activity for today."""
    print("Querying database for recent activity...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    time_now = datetime.now()
    time_15_mins_ago = time_now - timedelta(minutes=15)
    
    start_time_str = time_15_mins_ago.strftime('%Y-%m-%dT%H:%M:%S')
    
    query = """
    SELECT timestamp, activity_analysis FROM activity_log 
    WHERE timestamp >= ?
    """
    
    cursor.execute(query, (start_time_str,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print("No new activity found in the last 15 minutes.")
        return None

    aggregated_data = []
    for row in rows:
        timestamp, analysis_json_str = row
        try:
            analysis_data = json.loads(analysis_json_str)
            analysis_data['timestamp'] = timestamp # Add timestamp to the JSON object
            aggregated_data.append(analysis_data)
        except (json.JSONDecodeError, TypeError):
            # Skip malformed JSON data
            continue
            
    return aggregated_data

def execute_action(response_data):
    """Executes a function based on the LLM's response code."""
    try:
        code = int(response_data.get("execute_code"))
        comment = response_data.get("comment", "")
    except (TypeError, ValueError):
        print(f"Error: Invalid response format from LLM: {response_data}")
        return

    print(f"Received code: {code}, comment: '{comment}'")

    if not comment: # Don't show empty notifications
        print("No action needed.")
        return

    if code == 1:
        # Praise the user
        notification.notify(
            title='Janus: Great Work! 🚀',
            message=comment,
            timeout=10
        )
    elif code == 0:
        # Nudge the user
        notification.notify(
            title='Janus: Accountability Check ⚠️',
            message=comment,
            timeout=15
        )
    elif code == 2:
        # Block distracting sites for a duration
        try:
            distracting_sites = comment.get("distracting_sites", [])
            duration = int(comment.get("duration", 600)) # default to 10 minutes if not specified
            if distracting_sites and duration > 0:
                block_for_duration(duration, distracting_sites)
                notification.notify(
                    title='Janus: Blocking Distracting Sites 🚫',
                    message=f"Blocked {', '.join(distracting_sites)} for {duration//60} minutes.",
                    timeout=15
                )
            else:
                print("No distracting sites or invalid duration provided.")
        except (AttributeError, TypeError, ValueError) as e:
            print(f"Error processing blocking command: {e}")
    # code == -1 is handled by the "if not comment" check above


def update_activity_summary_of_day():
    SYSTEM_PROMPT_SUMMARY = """
    Give me the updated summary of today's activity based on the provided data.
    Respond ONLY with a valid JSON object with the following.
    
    example:
        {
            "date": "2025-09-05",
            "total_active_time_minutes": 320,
            "productivity_score_percent": 75,
            "timeline_log": [
                "08:30 - Started working on 'Project Janus' in VS Code.",
                "09:15 - Switched to Google Chrome for research on 'Python threading'.",
                "09:45 - Got distracted on YouTube.",
                "10:00 - Resumed work in the Terminal for 'Project Janus'.",
                "12:30 - Took a break (Idle)."
            ],
            "time_by_category": {
                "Productive": 240,
                "Neutral": 50,
                "Distracting": 30
            },
            "time_by_application": {
                "VS Code": 180,
                "Google Chrome": 60,
                "Terminal": 45,
                "YouTube": 25,
                "System Settings": 10
            }
        }

    Update this summary as you receive new activity data throughout the day.
"""

    chat_session = load_chat_session(SYSTEM_PROMPT_SUMMARY)
    response = chat_session.send_message("give me the updated summary of today's activity based on the provided chat.")
                
    # Clean up response in case it's wrapped in markdown
    cleaned_response_text = response.text.strip().replace('```json', '').replace('```', '').strip()
    llm_response_data = json.loads(cleaned_response_text)

    # Save the updated summary to a file
    summary_path = os.path.join(ACTIVITY_DATA_DIR, f'activity_summary_{datetime.now().strftime("%Y-%m-%d")}.json')
    write_file(summary_path, llm_response_data)
    print(f"Updated activity summary saved to {summary_path}")

# Update /user_data/user_behaviour file: Call this function at the boot time every day to update previous day's summary. -- pending
def update_user_behaviour_file():
    """Updates the user behaviour file with the previous day's summary."""
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    summary_path = os.path.join(ACTIVITY_DATA_DIR, f'activity_summary_{yesterday_str}.json')
    
    if not os.path.exists(summary_path):
        print(f"No summary file found for {yesterday_str}. Skipping user behaviour update.")
        return
    
    with open(summary_path, 'r') as f:
        summary_data = json.load(f)

    the_day_before_yesterday_str = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    user_behaviour_path = os.path.join(ACTIVITY_DATA_DIR, f'user_behaviour_{the_day_before_yesterday_str}.json')

    if os.path.exists(user_behaviour_path):
        with open(user_behaviour_path, 'r') as f:
            user_behaviour_data = json.load(f)
    else:
        user_behaviour_data = {}


    USER_PROMPT = f"""
    This is the user's behaviour data:
    <user_behaviour_data>
    {json.dumps(user_behaviour_data, indent=2)}
    </user_behaviour_data>

    And this is the summary of today's activity:
    <today_summary>
    {json.dumps(summary_data, indent=2)}
    </today_summary>

    Based on this data, update insights into the user's productivity patterns, habits, and areas for improvement.
    Respond ONLY with a valid JSON object to update the user behaviour data.
    """

    model = genai.GenerativeModel("gemini-2.5-pro")

    response = model.generate_content(USER_PROMPT)
    # Clean up response in case it's wrapped in markdown
    cleaned_response_text = response.text.strip().replace('```json', '').replace('```', '').strip()
    llm_response_data = json.loads(cleaned_response_text)

    user_behaviour_data = llm_response_data

    write_file(user_behaviour_path, user_behaviour_data)
    print(f"User behaviour file updated with data from {yesterday_str}.")

    # Change the file name of user_behaviour to the previous date from the day before yesterday
    user_behaviour_path = os.path.join(ACTIVITY_DATA_DIR, f'user_behaviour_{the_day_before_yesterday_str}.json')
    os.rename(user_behaviour_path, os.path.join(ACTIVITY_DATA_DIR, f'user_behaviour_{yesterday_str}.json'))
    print(f"Renamed user behaviour file to correspond to {yesterday_str}.")

# --- FILE OPERATIONS ---
def write_file(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return {"status": "success", "message": f"File {os.path.basename(filepath)} updated."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# --- MAIN EXECUTION LOOP ---

def main():
    """The main function that runs the 15-minute loop."""
    setup_environment()

    # run the user behaviour update only if the previous day's file doesn't exist
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    user_behaviour_path = os.path.join(ACTIVITY_DATA_DIR, f'user_behaviour_{yesterday_str}.json')
    if not os.path.exists(user_behaviour_path):
        update_user_behaviour_file()

    while True:
        print(f"\n--- Starting new cycle at {datetime.now()} ---")
        chat_session = load_chat_session(SYSTEM_PROMPT)
        # 1. Get data from the database
        recent_activity = get_recent_activity_data()
        
        if recent_activity:
            # 2. Prepare data and send to Gemini
            data_payload = json.dumps(recent_activity, indent=2)
            print("Sending data to Gemini...")
            
            try:
                response = chat_session.send_message(data_payload)
                
                # Clean up response in case it's wrapped in markdown
                cleaned_response_text = response.text.strip().replace('```json', '').replace('```', '').strip()
                llm_response_data = json.loads(cleaned_response_text)
                
                # 3. Execute action based on response
                execute_action(llm_response_data)
                
                # 4. Save the updated chat history
                save_chat_history(chat_session)
                
            except Exception as e:
                print(f"An error occurred during the Gemini API call or processing: {e}")


        ## 6. Update the activity summary of the day every hour
        #current_minute = datetime.now().minute
        #if current_minute >= 45:  # At the start of every hour
        update_activity_summary_of_day()

        # 5. Wait for the next cycle
        print("Cycle finished. Waiting for 15 minutes...")
        time.sleep(900) # 15 minutes * 60 seconds

if __name__ == "__main__":
    main()