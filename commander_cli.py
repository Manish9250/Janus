import os
import json
from datetime import datetime
from pathlib import Path
from re import escape
import google.generativeai as genai
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
import sqlite3
from datetime import datetime, timedelta

from code_executor import run_code

# --- CONFIGURATION ---
load_dotenv()
DB_PATH = 'database/activity_log_gemini.db'
DATA_DIR = 'user_data'
CHAT_HISTORY_DIR = 'chat_history'
USER_PROFILE_FILE = os.path.join(DATA_DIR, 'user_profile.json')
TASKS_FILE = os.path.join(DATA_DIR, 'tasks.json')
BEHAVIOR_FILE = os.path.join(DATA_DIR, 'user_behavior.json')
TODAYS_PLAN_FILE = os.path.join(DATA_DIR, 'todays_plan.json')
LLM_INFO_FILE = os.path.join(DATA_DIR, 'additional_llm_info.json')
# reading llm info file to add it to system prompt
os.makedirs(DATA_DIR, exist_ok=True)
with open(LLM_INFO_FILE, 'r') as f:
    llm_info = f.read()



API_KEY = os.getenv('GENAI_API_KEY_3')
if not API_KEY: raise ValueError("GENAI_API_KEY_2 not set.")
genai.configure(api_key=API_KEY)

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = f"""
You are Janus, a personal AI assistant. Your purpose is to help the user.

The JSON object must have a "response_type" key.
1.  If you want to have a conversation, set "response_type" to "conversation" and put your reply in a "comment" key.
2.  If you need to use a tool, set "response_type" to "tool_use" and add the "tool_name" and "parameters" keys.
3.  Whenever you find new info about me first update that into files.

**Example 1: Conversational Reply**
{{
  "response_type": "conversation",
  "comment": "Of course, I can help you with that."
}}

**Example 2: Tool Use**
{{
  "response_type": "tool_use",
  "tool_name": "read_tasks",
  "parameters": {{}}
}}

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
12. `get_project_structure(target_path)`: Retrieves the project's folder structure. Provide the target path as a string parameter. For current directories, use "." as the path. Always provide a target path.
13. `read_any_file(file_path)`: Reads the content of any file given its path. Supported file types: .json, .txt, .md, .csv, .sh, .py. Returns an error message if the file does not exist or is of an unsupported type.
14. `write_any_file(file_path, data)`: Writes data to any file given its path. Supported file types: .json, .txt, .md, .csv, .sh, .py. The 'data' parameter should be the content to write. Creates the file if it does not exist.
15. `current_time()`: Returns the current date and time in the format "YYYY-MM-DD HH:MM:SS".
16. `run_code(code, timeout_seconds)`: Executes provided Python code in a secure sandboxed environment. The 'code' parameter is a string of Python code to execute. The 'timeout_seconds' parameter is an integer specifying the maximum execution time in seconds.

**Important Instructions:**
1. I am using rich python library so format you conversation based in rich markdown.
2. Do one thing at a time. Use a tool or have a conversation, but not both at the same time.also complete the task like if you want to call multiple tools then do it one by one and only start the conversation after the tool calls are done.
3. You can shorten the conversation_history by summarizing it if it gets too long. Conversation_history is stored in chat_history folder. The file with name conversation_history_YYYY-MM-DD.json is the current file used. use write_any_file tool to add a new block to the json file following the structure like
    example: 
        [{{
            "role": "model",
            "parts": [
            "<summary here>"
            ]
        }}
        ]
4. You MUST ALWAYS respond with a single, valid JSON object. Do not add any text before or after the JSON object.
5. If you want to use tool then don't add any other text except the JSON object.

<additional_llm_info>
{llm_info}
</additional_llm_info>
"""

# --- TOOL FUNCTIONS ---

# Function to read the data from any file type provided the path
def read_any_file(file_path):
    if not os.path.exists(file_path):
        return {"status": "error", "message": f"File {os.path.basename(file_path)} does not exist."}
    try:
        with open(file_path, 'r') as f:
            if file_path.endswith('.json'):
                return json.load(f)
            elif file_path.endswith('.txt'):
                return {"content": f.read()}
            elif file_path.endswith('.md'): # markdown file
                return {"content": f.read()}
            elif file_path.endswith('.csv'): # CSV file
                import pandas as pd
                df = pd.read_csv(f)
                return df.to_dict(orient='records')
            # .sh file
            elif file_path.endswith('.sh'):
                return {"content": f.read()}
            # .py file
            elif file_path.endswith('.py'):
                return {"content": f.read()}
            else:
                return {"status": "error", "message": "Unsupported file type."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def read_file(filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def write_file(filepath, data):
    """
    Writes data to a file, intelligently handling different data types.

    This function will:
    - Create the directory for the filepath if it doesn't exist.
    - If the filepath ends with '.json' and the data is a dictionary or list,
      it will dump the data as a JSON string.
    - If the data is in bytes, it will write it in binary mode. This is
      suitable for non-text files like executables, images, etc.
    - If the data is a string, it will write it in text mode. This is
      suitable for files like .py, .txt, .html, etc.
    - If the data type is not supported, it will raise a TypeError.

    Args:
        filepath (str): The full path to the file to be written.
        data (dict, list, str, bytes): The data to write to the file.

    Returns:
        dict: A dictionary containing the status ("success" or "error")
              and a corresponding message.
    """
    try:
        # Create the directory if it doesn't exist.
        # This handles cases where the filepath is just a filename in the current directory.
        dir_name = os.path.dirname(filepath)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
    except Exception as e:
        print(f"Error creating directory for '{filepath}': {e}")
        return {"status": "error", "message": f"Directory creation failed: {e}"}

    try:
        # --- File Writing Logic ---

        # For .json files, if data is a dict or list, dump it as JSON.
        if filepath.endswith('.json') and isinstance(data, (dict, list)):
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)

        # For binary data, open in write-binary ('wb') mode.
        elif isinstance(data, bytes):
            with open(filepath, 'wb') as f:
                f.write(data)

        # For string data, open in standard write ('w') mode.
        elif isinstance(data, str):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(data)

        # Handle unsupported data types.
        else:
            raise TypeError(
                "Unsupported data type. Data must be a str, bytes, or a dict/list for .json files."
            )

        # If everything succeeded, return a success message.
        return {"status": "success", "message": f"File '{os.path.basename(filepath)}' was written successfully."}

    except Exception as e:
        print(f"Error writing to file '{filepath}': {e}")
        return {"status": "error", "message": str(e)}

# get the file structure of provided path
def get_project_structure(target_path="."):
    """
    Returns the top-level directory structure for a given path.
    
    Args:
        target_path (str): The path to the folder to search. 
                           Defaults to the current directory (".").
    """
    # Convert the incoming string path into a Path object
    search_path = Path(target_path)

    # Safety check: Make sure the path exists and is a directory
    if not search_path.is_dir():
        print(f"Error: Path '{search_path}' is not a valid directory.")
        return {} # Return an empty dictionary on error

    # Use iterdir() for a non-recursive listing of the given path
    return {
        path.name: path.name 
        for path in search_path.iterdir()
    }

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
    "get_project_structure": lambda target_path: get_project_structure(target_path),
    "read_any_file": lambda file_path: read_any_file(file_path),
    # tool that will use write_file function to write data to any file
    "write_any_file": lambda file_path, data: write_file(file_path, data),
    "current_time": lambda: {"current_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
    "run_code": lambda code, timeout_seconds=5: run_code(code, timeout_seconds),

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
            chat_history = json.load(f)
            chat_history_length = len(json.dumps(chat_history))
            print(f"Loaded {len(chat_history)}({chat_history_length}) messages from chat history.")
            if chat_history_length > 200000:  # If history exceeds 200k characters, truncate it
                print("Chat history too long, truncating to last 10 messages.")
                return chat_history[-10:]
            return chat_history
    return []

def save_chat_history(history):
    history_path = get_chat_history_path()
    serializable_history = [
        {"role": msg.role, "parts": [part.text for part in msg.parts]} for msg in history
    ]
    with open(history_path, 'w') as f:
        json.dump(serializable_history, f, indent=2)


# Function that runs for the first time and llm a call with the current date and time, ask it to read all the files and respond with a message that seems appropriate. based on user history.
def say_hello():
    user_input = f"Hello Janus, today is {datetime.now().strftime('%A, %B %d, %Y')}. This is a system generated request to read the files and based on all the data of user reponse with a message that seems appropriate. Also if this step is already done in the chat history then just greet the user with a message that seems appropriate."
    return user_input

# --- MAIN LOGIC ---
def main():
    """The main CLI loop for the Commander."""
    console = Console()
    
    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        system_instruction=SYSTEM_PROMPT,
        generation_config={"response_mime_type": "application/json"}
    )
    history = load_chat_history()
    chat = model.start_chat(history=history)
    
    console.print("--- Janus CLI Assistant ---", style="bold yellow")
    console.print("Type 'exit' or 'quit' to end the session.")

    first_interaction = True
    while True:
        if len(history) == 0 and first_interaction:
            user_input = say_hello()
            first_interaction = False
        else:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
        if user_input.lower() in ['exit', 'quit']:
            break

        # add timestamp to user input
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user_input = f"[{timestamp}] {user_input}"

        response = chat.send_message(user_input + "<system added instrution > Remember to respond with a single, valid JSON object as per the instructions. Do one thing at a time either use tool or do conversation. <system added instrution>")
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
                console.print(f"[bold white on black][bold green]Janus[/bold green]: {comment}[/bold white on black]")
                return
            except Exception as e:
                console.print(f"[bold red]Error processing conversation response:[/bold red]")
                print(e)
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
                        console.print(f"[bold red]Error sending tool result to chat:[/bold red]")
                        print(e)
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
                console.print(f"[bold red]Error executing tool:[/bold red]")
                print(e)
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