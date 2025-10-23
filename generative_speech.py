# File: audio_generator.py

import mimetypes
import os
import struct
import traceback
import threading  # <-- NEW IMPORT
import google.generativeai as genai

# NEW IMPORT for playing the audio
from playsound import playsound



#
# THIS IS THE NEW FUNCTION YOU WILL CALL FROM YOUR MAIN FILE
#
def speak(text_to_speak: str, key_rotator):
    """
    Starts the audio generation and playback on a new background thread.
    This function returns immediately.
    """
    # Create a new thread object
    # target = the function to run in the background
    # args = the arguments to pass to that function (must be a tuple)
    # daemon = True means the thread will automatically exit when the main program quits
    thread = threading.Thread(
        target=_speak_blocking, 
        args=(text_to_speak, key_rotator), 
        daemon=True
    )
    
    # Start the background thread
    thread.start()


#
# RENAMED your old 'speak' function to '_speak_blocking'
#
def _speak_blocking(text_to_speak: str, key_rotator):
    """
    The ACTUAL work: generates audio, plays it, and deletes the file.
    This function runs in the background and is 'blocking'.
    """
    # print("---------------------------------")
    # print(f"BG Thread: Requesting speech for: '{text_to_speak}'")

    audio_file = _generate_audio_file(text_to_speak, key_rotator)

    if audio_file:
        # print(f"BG Thread: Playing {audio_file}...")
        playsound(audio_file)
        try:
            os.remove(audio_file)
            # print(f"BG Thread: Deleted temporary file: {audio_file}")
        except OSError as e:
            pass
            # print(f"BG Thread: Error deleting file {audio_file}: {e}")


#
# Renamed 'generate_audio_file' to '_generate_audio_file'
#
def _generate_audio_file(text_prompt: str, key_rotator) -> str | None:
    """
    Generates an audio file from text and returns the filename.
    Returns None on failure.
    """
    try:
        current_key_for_llm = next(key_rotator) # Rotate to the next API key
        genai.configure(api_key=current_key_for_llm)
    except Exception as e:
        # print(f"BG Thread: Error configuring API key: {e}")
        return None

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-tts"
    )

    contents = [{"role": "user", "parts": [{"text": text_prompt}]}]
    
    generate_content_config = {
        "temperature": 0.5,
        "response_modalities": ["AUDIO"],
        "speech_config": {
            "voice_config": {"prebuilt_voice_config": {"voice_name": "Zephyr"}}
        },
    }

    output_filename = f"temp_audio_{threading.get_ident()}.wav" # Unique name per thread
    audio_saved = False
    
    print("BG Thread: Generating audio...")
    
    for _ in range(2):  # Try up to 2 times
        
        try:
            current_key_for_llm = next(key_rotator) # Rotate to the next API key
            genai.configure(api_key=current_key_for_llm)
            for chunk in model.generate_content(
                contents=contents,
                generation_config=generate_content_config,
                stream=True,
            ):
                if (
                    chunk.candidates is None
                    or chunk.candidates[0].content is None
                    or chunk.candidates[0].content.parts is None
                ):
                    continue

                for part in chunk.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        inline_data = part.inline_data
                        data_buffer = convert_to_wav(inline_data.data, inline_data.mime_type)
                        _save_binary_file(output_filename, data_buffer)
                        audio_saved = True

        except Exception as e:
            continue  # Try again with a new API key
        if audio_saved:
            return output_filename
        else:
            # print("BG Thread: No audio data was returned.")
            return None

# --- Helper functions are unchanged, just added underscores ---

def _save_binary_file(file_name, data):
    with open(file_name, "wb") as f:
        f.write(data)
    # print(f"BG Thread: File saved to: {file_name}")

# THIS IS THE NEW, FIXED FUNCTION
def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """Generates a WAV file header for the given audio data and parameters."""
    
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    
    if bits_per_sample is None or sample_rate is None:
        bits_per_sample = 16
        sample_rate = 24000
        # print("Warning: Could not parse audio metadata, defaulting to 16-bit, 24kHz.")

    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    # This struct.pack call is now correct and has 13 arguments
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # 1
        chunk_size,       # 2 (This was the missing argument)
        b"WAVE",          # 3
        b"fmt ",          # 4
        16,               # 5
        1,                # 6
        num_channels,     # 7
        sample_rate,      # 8
        byte_rate,        # 9
        block_align,      # 10
        bits_per_sample,  # 11
        b"data",          # 12
        data_size         # 13
    )
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    bits_per_sample = 16
    rate = 24000
    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try: rate = int(param.split("=", 1)[1])
            except (ValueError, IndexError): pass 
        elif param.startswith("audio/L"):
            try: bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError): pass 
    return {"bits_per_sample": bits_per_sample, "rate": rate}


# --- This block is for testing the file directly ---
if __name__ == "__main__":
    import time
    if "GEMINI_API_KEY" not in os.environ:
        print("ERROR: GEMINI_API_KEY environment variable not set.")
    else:
        print("Main Thread: Calling speak() for 'Hello'.")
        speak("Hello! This audio should play in the background.")
        
        # This will print immediately, while the audio is still generating
        print("Main Thread: The 'speak' function returned instantly.")
        time.sleep(1)
        print("Main Thread: I'm in my 'main loop' doing other work...")
        
        speak("This is a second sentence, which might overlap the first.")
        
        print("Main Thread: Waiting for 10 seconds for audio to finish...")
        time.sleep(10)
        print("Main Thread: Exiting.")