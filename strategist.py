import sqlite3
import json
import os
import time
from datetime import datetime, timedelta
import google.generativeai as genai
from plyer import notification
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv()
DB_PATH = 'activity_log_gemini.db'
CHAT_HISTORY_DIR = 'chat_history'
API_KEY = os.getenv('GEMINI_API_KEY')

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are Janus, an AI accountability coach. Your purpose is to help the user stay focused and productive.

You will receive a summary of the user's computer activity in a JSON format. Your task is to analyze this data and respond ONLY with a valid JSON object.

The JSON object must have two keys: "comment" and "execute_code".

Use the "execute_code" to categorize the user's status based on the following rules:
- "execute_code": 1 -> The user is being highly productive and deserves praise. The "comment" should be a short, encouraging message.
- "execute_code": 0 -> The user is distracted or has lost focus. The "comment" should be a firm but helpful nudge to get them back on track.
- "execute_code": -1 -> The user's activity is neutral, balanced, or there is not enough data. No action is needed. The "comment" should be an empty string.

Do not use any other codes. Analyze the following user data and provide your JSON response without any additional text or formatting.
"""

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

def load_chat_session():
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
    # code == -1 is handled by the "if not comment" check above

# --- MAIN EXECUTION LOOP ---

def main():
    """The main function that runs the 15-minute loop."""
    setup_environment()
    
    while True:
        print(f"\n--- Starting new cycle at {datetime.now()} ---")
        chat_session = load_chat_session()
        
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

        # 5. Wait for the next cycle
        print("Cycle finished. Waiting for 15 minutes...")
        time.sleep(900) # 15 minutes * 60 seconds

if __name__ == "__main__":
    main()