#!/bin/bash

# --- Go to the Project Directory ---
# This command automatically changes the directory to wherever the script itself is located.
# This ensures all relative paths work correctly, no matter where you run the script from.
cd "$(dirname "$0")"

# --- Configuration ---
# Now that we're in the correct directory, we can use simple relative paths.
SESSION_NAME="JanusProject"
VENV_PATH="./venv"
SCRIPT_1_PATH="./commander_cli.py"
SCRIPT_2_PATH="./activity_monitor_gemini.py"
SCRIPT_3_PATH="./strategist.py"

# --- Script Logic ---
# Check if a session with the same name already exists. If not, create it.
# NOTE: This script must be run with sudo for the Python scripts to have root access.
tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? != 0 ]; then
  echo "Creating new tmux session: $SESSION_NAME"
  
  # Start a new, detached tmux session
  tmux new-session -d -s $SESSION_NAME
  
  # --- Pane Setup ---
  tmux split-window -v -t $SESSION_NAME:0.0
  tmux split-window -h -t $SESSION_NAME:0.1
  
  # --- Run Scripts in Panes using the venv ---
  # This part remains the same. It will now execute from the project directory.
  tmux send-keys -t $SESSION_NAME:0.0 "$VENV_PATH/bin/python $SCRIPT_1_PATH" C-m
  tmux send-keys -t $SESSION_NAME:0.1 "$VENV_PATH/bin/python $SCRIPT_2_PATH" C-m
  tmux send-keys -t $SESSION_NAME:0.2 "$VENV_PATH/bin/python $SCRIPT_3_PATH" C-m
  
  # Select the top pane to be the active one.
  tmux select-pane -t $SESSION_NAME:0.0

fi

# Attach to the session
echo "Attaching to session: $SESSION_NAME"
tmux attach-session -t $SESSION_NAME