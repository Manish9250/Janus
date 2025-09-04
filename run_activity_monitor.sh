#!/bin/bash

# This script navigates to the project directory, activates the virtual environment,
# and then executes the Python activity monitor script.

# --- Configuration ---
# The absolute path to your project directory
PROJECT_DIR="/home/manish/shared_space/Janus"
# The name of your virtual environment folder
VENV_NAME="venv"
# The name of your Python script
PYTHON_SCRIPT="activity_monitor_gemini.py"


# --- Script Execution ---

# 1. Navigate to the project directory
echo "Changing directory to $PROJECT_DIR..."
cd "$PROJECT_DIR" || { echo "Error: Directory $PROJECT_DIR not found. Exiting."; exit 1; }

# 2. Activate the virtual environment
# Assumes the venv is inside the project directory.
VENV_PATH="$PROJECT_DIR/$VENV_NAME/bin/activate"
if [ -f "$VENV_PATH" ]; then
    echo "Activating virtual environment..."
    source "$VENV_PATH"
else
    echo "Error: Virtual environment not found at $VENV_PATH. Exiting."
    exit 1
fi

# 3. Run the Python script
echo "Running Python script: $PYTHON_SCRIPT..."
python "$PYTHON_SCRIPT"

# 4. Deactivate the virtual environment (optional, as the script will exit anyway)
echo "Script finished. Deactivating virtual environment."
deactivate

echo "Done."
