import os
import time
import json
import sqlite3
from datetime import datetime
import mss
import easyocr
import google.generativeai as genai
from dotenv import load_dotenv

# --- Configuration ---
CAPTURE_INTERVAL_SECONDS = 150  # 5 minutes
DB_PATH = "database/activity_log_gemini.db"
SCREENSHOT_DIR = "screenshots"
GEMINI_MODEL_NAME = "gemini-2.5-flash-lite"

# --- Foundational Components ---

def capture_fullscreen(sct, output_dir: str) -> str:
    """Captures a screenshot of the entire virtual screen."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    timestamp = int(time.time())
    filename = f"screenshot_{timestamp}.png"
    output_path = os.path.join(output_dir, filename)
    sct.shot(mon=-1, output=output_path)
    return output_path

def extract_text_from_image(reader, image_path: str) -> str:
    """Extracts text from an image file using easyocr."""
    try:
        results = reader.readtext(image_path, detail=0, paragraph=True)
        return "\n".join(results)
    except Exception as e:
        print(f"Error during OCR: {e}")
        return ""

def initialize_database(db_path: str):
    """Creates the SQLite database and table if they don't exist."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                screenshot_path TEXT NOT NULL,
                ocr_text TEXT,
                activity_analysis TEXT
            )
        """)
        conn.commit()

def log_activity(db_path: str, screenshot_path: str, ocr_text: str, analysis: str):
    """Logs a new activity record to the database."""
    timestamp = datetime.now().isoformat()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        sql = ''' INSERT INTO activity_log(timestamp, screenshot_path, ocr_text, activity_analysis)
                  VALUES(?,?,?,?) '''
        cursor.execute(sql, (timestamp, screenshot_path, ocr_text, analysis))
        conn.commit()

# --- Gemini Analysis Component ---

def configure_gemini():
    """Configures the Gemini API with an API key."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Please set it in a.env file.")
    genai.configure(api_key=api_key)
    

def analyze_text_with_gemini(model, ocr_text: str) -> str:
    """Analyzes OCR text using the Gemini API."""
    prompt = f"""
    You are an expert user activity analyst. Analyze the following text extracted from a user's screen and infer their current activity.
    Provide your analysis in a single, valid JSON object with keys: "application", "activity", and "topics".
    If the text is insufficient, return null values.

    OCR Text:
    ---
    {str(ocr_text)}
    ---
    """
    try:
        generation_config = genai.types.GenerationConfig(temperature=0)

        response = model.generate_content(prompt, generation_config=generation_config)
        json_text = response.text.strip().replace("```json", "").replace("```", "").strip()
        json.loads(json_text)
        return json_text
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        return json.dumps({"application": None, "activity": "Error during analysis", "topics": [str(e)]})

# --- Main Orchestrator ---

def main():
    """Main loop for the activity monitor."""

    print("Clearing previous screenshots...")
    if os.path.exists(SCREENSHOT_DIR):
        for f in os.listdir(SCREENSHOT_DIR):
            os.remove(os.path.join(SCREENSHOT_DIR, f))
    else:
        os.makedirs(SCREENSHOT_DIR)


    print("Initializing Gemini-based activity monitor...")
    try:
        sct = mss.mss()
        configure_gemini()
        gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        ocr_reader = easyocr.Reader(['en'], gpu=True)
        initialize_database(DB_PATH)
    except Exception as e:
        print(f"Initialization failed: {e}")
        return

    print("Monitor started. Press Ctrl+C to stop.")
    while True:
        try:
            timestamp_start = datetime.now()
            print(f"[{timestamp_start}] Starting new capture cycle...")

            screenshot_file = capture_fullscreen(sct, SCREENSHOT_DIR)
            print(f"  - Screenshot saved: {screenshot_file}")

            ocr_text = extract_text_from_image(ocr_reader, screenshot_file)
            print(f"  - OCR complete: Extracted {len(ocr_text)} characters.")

            analysis_json = analyze_text_with_gemini(gemini_model, ocr_text)
            print(f"  - Gemini analysis complete.")

            log_activity(DB_PATH, screenshot_file, ocr_text, analysis_json)
            print(f"  - Activity logged to {DB_PATH}.")

            print(f"Cycle complete. Waiting for {CAPTURE_INTERVAL_SECONDS} seconds...")
            time.sleep(CAPTURE_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            print("\nMonitor stopped by user.")
            break
        except Exception as e:
            print(f"An error occurred in the main loop: {e}")
            time.sleep(CAPTURE_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()