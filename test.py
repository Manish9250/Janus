import psutil

# A list of common browser process names on Linux/Ubuntu.
# You can add or remove names based on the browsers you use.
BROWSER_PROCESSES = [
    "chrome", 
    "firefox", 
    "brave-browser", 
    "opera",
    "chromium-browser"
] 

def close_all_browsers():
    """
    Finds and gracefully terminates all running browser processes 
    from the BROWSER_PROCESSES list.
    """
    print("🚀 Starting browser shutdown for focus session...")
    browsers_closed = 0

    # Iterate through all running processes on the system
    for process in psutil.process_iter(['name']):
        # Check if the process name is in our target list
        if process.info['name'] in BROWSER_PROCESSES:
            try:
                print(f"   -> Found running browser: '{process.info['name']}'. Terminating...")
                process.terminate()  # Sends a graceful shutdown signal
                browsers_closed += 1
            except psutil.NoSuchProcess:
                # This can happen if the process closes between finding it and terminating it
                print(f"   -> Could not terminate '{process.info['name']}', it may have already closed.")
            except psutil.AccessDenied:
                print(f"   -> ⚠️ Access denied. Could not terminate '{process.info['name']}'. Try running the script with sudo.")

    if browsers_closed > 0:
        print(f"\n✅ Successfully closed {browsers_closed} browser process(es).")
    else:
        print("\n👍 No targeted browsers were found running.")

# This part allows you to run the script directly from the terminal for testing.
if __name__ == "__main__":
    close_all_browsers()