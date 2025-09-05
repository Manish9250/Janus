import os
import json
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
import sqlite3
from datetime import datetime, timedelta

# --- CONFIGURATION ---
load_dotenv()
DB_PATH = 'activity_log_gemini.db'
DATA_DIR = 'user_data'
CHAT_HISTORY_DIR = 'chat_history'
USER_PROFILE_FILE = os.path.join(DATA_DIR, 'user_profile.json')
TASKS_FILE = os.path.join(DATA_DIR, 'tasks.json')
BEHAVIOR_FILE = os.path.join(DATA_DIR, 'user_behavior.json')
LLM_INFO_FILE = os.path.join(DATA_DIR, 'additional_llm_info.json')
TODAYS_PLAN_FILE = os.path.join(DATA_DIR, 'todays_plan.json')

API_KEY = os.getenv('GENAI_API_KEY_2')
if not API_KEY: raise ValueError("GENAI_API_KEY_2 not set.")
genai.configure(api_key=API_KEY)

# --- SYSTEM PROMPT ---
# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are Janus, a personal AI assistant. Your purpose is to help the user.

The JSON object must have a "response_type" key.
1.  If you want to have a conversation, set "response_type" to "conversation" and put your reply in a "comment" key.
2.  If you need to use a tool, set "response_type" to "tool_use" and add the "tool_name" and "parameters" keys.
3.  Whenever you find new info about me first update that into files.

**Example 1: Conversational Reply**
{
  "response_type": "conversation",
  "comment": "Of course, I can help you with that."
}

**Example 2: Tool Use**
{
  "response_type": "tool_use",
  "tool_name": "read_tasks",
  "parameters": {}
}

1.  `read_user_profile()`: Reads the user's personal profile.
2.  `read_tasks()`: Reads the user's goals and tasks.
3.  `read_user_behavior()`: Reads observations about the user's habits.
4.  `read_llm_info()`: Reads your own internal notes for self-reflection.
5.  `update_user_profile(updated_profile)`: Overwrites the user profile. Provide the complete, updated JSON object.
6.  `update_tasks(updated_tasks)`: Overwrites the task list. Provide the complete, updated JSON object.
7.  `update_user_behavior(updated_behavior)`: Overwrites the user behavior file. Provide the complete, updated JSON object.
8.  `update_llm_info(updated_info)`: Overwrites your internal notes file. Provide the complete, updated JSON object.
9.  `get_recent_activity_data(minutes)`: Retrieves the user's computer activity data from the last 'minutes' minutes. Provide the number of minutes as an integer parameter.
10. `read_todays_plan()`: Reads the user's plan for today.
11. `update_todays_plan(updated_plan)`: Overwrites today's plan.

You MUST ALWAYS respond with a single, valid JSON object. Do not add any text before or after the JSON object.
"""

# --- TOOL FUNCTIONS ---
def read_file(filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def write_file(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return {"status": "success", "message": f"File {os.path.basename(filepath)} updated."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_recent_activity_data(minutes=60):
    """Queries the DB for the last 'minutes' of activity for today."""
    print(f"Querying database for recent activity in the last {minutes} minutes...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    time_now = datetime.now()
    time_x_mins_ago = time_now - timedelta(minutes=minutes)

    start_time_str = time_x_mins_ago.strftime('%Y-%m-%dT%H:%M:%S')

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


TOOL_MAPPING = {
    "read_user_profile": lambda: read_file(USER_PROFILE_FILE),
    "read_tasks": lambda: read_file(TASKS_FILE),
    "read_user_behavior": lambda: read_file(BEHAVIOR_FILE),
    "read_llm_info": lambda: read_file(LLM_INFO_FILE),
    "update_user_profile": lambda updated_profile: write_file(USER_PROFILE_FILE, updated_profile),
    "update_tasks": lambda updated_tasks: write_file(TASKS_FILE, updated_tasks),
    "update_user_behavior": lambda updated_behavior: write_file(BEHAVIOR_FILE, updated_behavior),
    "update_llm_info": lambda updated_info: write_file(LLM_INFO_FILE, updated_info),
    "get_recent_activity_data": lambda minutes: get_recent_activity_data(minutes),
    "read_todays_plan": lambda: read_file(TODAYS_PLAN_FILE),
    "update_todays_plan": lambda updated_plan: write_file(TODAYS_PLAN_FILE, updated_plan),

}

# --- CHAT HISTORY FUNCTIONS ---
def get_chat_history_path():
    today_str = datetime.now().strftime('%Y-%m-%d')
    os.makedirs(CHAT_HISTORY_DIR, exist_ok=True)
    return os.path.join(CHAT_HISTORY_DIR, f'conversation_history_{today_str}.json')

def load_chat_history():
    history_path = get_chat_history_path()
    if os.path.exists(history_path):
        with open(history_path, 'r') as f:
            return json.load(f)
    return []

def save_chat_history(history):
    history_path = get_chat_history_path()
    serializable_history = [
        {"role": msg.role, "parts": [part.text for part in msg.parts]} for msg in history
    ]
    with open(history_path, 'w') as f:
        json.dump(serializable_history, f, indent=2)

# --- MAIN LOGIC ---
# --- MAIN LOGIC ---
def main():
    """The main CLI loop for the Commander."""
    console = Console()
    
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        system_instruction=SYSTEM_PROMPT,
    )
    history = load_chat_history()
    chat = model.start_chat(history=history)
    
    console.print("--- Janus CLI Assistant ---", style="bold yellow")
    console.print("Type 'exit' or 'quit' to end the session.")

    while True:
        user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
        if user_input.lower() in ['exit', 'quit']:
            break

        response = chat.send_message(user_input + "\nRemember to respond with a single, valid JSON object as per the instructions.")
        cleaned_response_text = response.text.strip().replace('```json', '').replace('```', '').strip()
        
        # Calling the response processing function
        process_llm_response(chat, console, cleaned_response_text)    
        # Save chat history after each interaction
        save_chat_history(chat.history)

def process_llm_response(chat, console, cleaned_response_text):
    try:
        # We now expect every valid response to be a JSON object.
        response_json = json.loads(cleaned_response_text)
        response_type = response_json.get("response_type")

        if response_type == "conversation":
            try:
                comment = response_json.get("comment", "I'm not sure what to say.")
                console.print(f"[bold green]Janus[/bold green]: {comment}")
                return
            except Exception as e:
                console.print(f"[bold red]Error processing conversation response: {e}[/bold red]")
                return
        elif response_type == "tool_use":
            try:
                print("Tool use requested...", response_json)
                tool_name = response_json.get("tool_name")
                parameters = response_json.get("parameters", {})
                
                if tool_name in TOOL_MAPPING:
                    console.print(f"Executing tool: {tool_name}...", style="italic dim")
                    tool_function = TOOL_MAPPING[tool_name]
                    tool_result = tool_function(**parameters)
                    
                    try:
                        final_response = chat.send_message(f"Tool Result: {json.dumps(tool_result)}" + " Please respond with a JSON object as per the instructions.")
                    except Exception as e:  
                        console.print(f"[bold red]Error sending tool result to chat: {e}[/bold red]")
                        return
                    # The response to a tool result should also be a JSON object
                    try:
                        cleaned_response = final_response.text.strip().replace('```json', '').replace('```', '').strip()
                        process_llm_response(chat, console, cleaned_response)
                    except json.JSONDecodeError:
                        console.print("[bold red]Error: The AI's response after tool execution was not valid JSON.[/bold red]")
                        console.print(f"\n[bold]Problematic Text Received:[/bold]\n{final_response.text}")
                        return
                else:
                    console.print(f"[bold red]Janus: Error - I tried to use an unknown tool: {tool_name}[/bold red]")
                    return
            except Exception as e:
                console.print(f"[bold red]Error executing tool: {e}[/bold red]")
                return
        else:
            console.print(f"[bold red]Janus: Error - Received an unknown response type: {response_type}[/bold red]")
            return

    except json.JSONDecodeError:
        console.print("[bold red]Error: Failed to parse the AI's response as JSON. The AI did not follow instructions.[/bold red]")
        console.print(f"\n[bold]Problematic Text Received:[/bold]\n{cleaned_response_text}")
        return

if __name__ == "__main__":
    main()