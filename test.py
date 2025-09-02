import mss
import time
import os

def main():
    # Initialize mss ONCE, outside the loop
    sct = mss.mss(display=os.getenv("DISPLAY"))
    
    while True:
        # Now, just use the 'sct' object to take a screenshot
        screenshot_path = "screenshot.png"
        sct.shot(mon=-1, output=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        # In our full script, the OCR and LLM calls would go here
        
        time.sleep(10) # Wait 5 minutes

if __name__ == "__main__":
    main()

    