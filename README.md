# Project Janus: The Master Plan

## Project Goal
To create a proactive, voice-controlled personal assistant that observes user behavior, understands context, manages tasks, and provides multi-layered interventions to improve focus and productivity.

## Core Philosophy
**Local-First & Privacy-Focused.** All data processing, from screenshot analysis to AI reasoning, will be done on the user's local machine. User data will never leave the computer.

---
## Core Architecture: The Seven Modules

1.  **The Sentry (Data Collector):** Runs silently in the background, taking full-screen screenshots at a set interval.
2.  **The Investigator (AI Analyst):** Uses a local Llava model to analyze screenshots, understand activity, and output a structured JSON summary. The screenshot is deleted immediately after analysis.
3.  **The Chronicler (Database):** A SQLite database that stores the historical JSON data from the Investigator, building a long-term record of user behavior.
4.  **The Taskmaster (To-Do List):** A `tasks.json` file that is readable by the AI and can be edited via voice commands.
5.  **The Strategist (Pattern Analyst):** Periodically analyzes the Chronicler's database to identify unique behavioral patterns.
6.  **The Guardian (Intervention Engine):** The system's active enforcement arm. It uses data from all other modules to decide when and how to intervene to keep the user on task.
7.  **The Commander (Voice Interface):** The central hub for user interaction, using STT/TTS to handle voice commands and provide spoken feedback.

---
## Implementation Roadmap

### Phase 1: The Foundation (Core Observation Loop)
* **Goal:** Establish the passive, automated data collection system.
* **Steps:**
    1.  Setup the Ubuntu environment with NVIDIA drivers, CUDA, and Ollama.
    2.  Deploy a quantized Llava model via Ollama.
    3.  Build **The Sentry**: Create a script to take periodic full-screen screenshots.
    4.  Build **The Investigator**: Write logic to send screenshots to the local Llava model and receive JSON analysis.
    5.  Build **The Chronicler**: Set up the SQLite database and log the Investigator's output.

### Phase 2: The Interaction Layer (Voice & Task Management)
* **Goal:** Enable two-way voice communication and task management.
* **Steps:**
    1.  Create **The Taskmaster**: Define the structure for `tasks.json`.
    2.  Develop Tools: Write Python functions (`add_task()`, `remove_task()`, `get_tasks()`).
    3.  Build **The Commander**: Integrate your STT/TTS module and orchestrate the voice command workflow.

### Phase 3: The Intelligence Layer (Proactive Coaching)
* **Goal:** Make the assistant smart by teaching it your habits and enabling intervention.
* **Steps:**
    1.  Build **The Strategist**: Create the script to analyze the database for behavioral patterns.
    2.  Build **The Guardian**: Implement the logic for the tiered intervention system (nudge, appeal, friction, block).

### Phase 4: The Expansion (Superpowers)
* **Goal:** Grant the assistant advanced capabilities to interact with the outside world.
* **Steps:**
    1.  Develop a **Web Search Tool**.
    2.  Develop a secure **Code Execution Tool**.
    3.  Integrate these new tools into the Commander's available functions.

---
## Technology Stack

* **Language:** Python
* **AI Engine:** Ollama
* **AI Model:** Llava (quantized version)
* **Database:** SQLite
* **Core Libraries:** `mss`, `SpeechRecognition`/`gTTS` (or existing voice tools), `pvporcupine` (wake word), `requests`/`BeautifulSoup`.
* **Platform:** Ubuntu with NVIDIA RTX 2050.
