import mimetypes
import os
import struct
import traceback

# We only need the main genai import
import google.generativeai as genai

# NEW IMPORT for playing the audio
from playsound import playsound


def save_binary_file(file_name, data):
    """Saves raw binary data to a file."""
    with open(file_name, "wb") as f:
        f.write(data)
    print(f"File saved to: {file_name}")


def generate_audio_file(text_prompt: str) -> str | None:
    """
    Generates an audio file from text and returns the filename.
    Returns None on failure.
    """
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    except Exception as e:
        print(f"Error configuring API key: {e}")
        return None

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-preview-tts"
    )

    contents = [
        {
            "role": "user",
            "parts": [
                {"text": text_prompt}  # Use the text passed into the function
            ]
        }
    ]
    
    generate_content_config = {
        "temperature": 0.5,
        "response_modalities": ["AUDIO"],  # Must be uppercase
        "speech_config": {
            "voice_config": {
                "prebuilt_voice_config": {
                    "voice_name": "Zephyr"
                }
            }
        },
    }

    # Define a predictable temporary filename
    output_filename = "temp_audio_file.wav"
    audio_saved = False
    
    print("Generating audio... please wait.")
    
    try:
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

            # Check for audio parts and save them
            for part in chunk.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    inline_data = part.inline_data
                    data_buffer = inline_data.data
                    
                    # We assume it's raw PCM and needs a WAV header
                    data_buffer = convert_to_wav(inline_data.data, inline_data.mime_type)
                    
                    save_binary_file(output_filename, data_buffer)
                    audio_saved = True

    except Exception as e:
        print(f"\n--- AN ERROR OCCURRED DURING GENERATION ---")
        print(f"Error Message: {e}")
        traceback.print_exc()
        return None

    if audio_saved:
        return output_filename
    else:
        print("No audio data was returned.")
        return None


def speak(text_to_speak: str):
    """
    Generates audio from text, plays it, and then deletes the file.
    """
    print("---------------------------------")
    print(f"Requesting speech for: '{text_to_speak}'")
    
    # 1. Generate the audio file
    audio_file = generate_audio_file(text_to_speak)
    
    if audio_file:
        try:
            # 2. Play the audio file
            print("Playing audio...")
            playsound(audio_file)
        
        except Exception as e:
            print(f"Error playing audio file {audio_file}: {e}")
        
        finally:
            # 3. Delete the audio file
            try:
                os.remove(audio_file)
                print(f"Deleted temporary file: {audio_file}")
            except OSError as e:
                print(f"Error deleting file {audio_file}: {e}")
    else:
        print("Failed to generate audio file.")


# --- All helper functions below are unchanged ---

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
        print("Warning: Could not parse audio metadata, defaulting to 16-bit, 24kHz.")

    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",          # ChunkID
        chunk_size,       # ChunkSize
        b"WAVE",          # Format
        b"fmt ",          # Subchunk1ID
        16,               # Subchunk1Size
        1,                # AudioFormat (1 for PCM)
        num_channels,     # NumChannels
        sample_rate,      # SampleRate
        byte_rate,        # ByteRate
        block_align,      # BlockAlign
        bits_per_sample,  # BitsPerSample
        b"data",          # Subchunk2ID
        data_size         # Subchunk2Size
    )
    return header + audio_data

def parse_audio_mime_type(mime_type: str) -> dict[str, int | None]:
    """Parses bits per sample and rate from an audio MIME type string."""
    
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass 
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass 

    return {"bits_per_sample": bits_per_sample, "rate": rate}


if __name__ == "__main__":
    if "GEMINI_API_KEY" not in os.environ:
        print("ERROR: GEMINI_API_KEY environment variable not set.")
        print("Please set it before running: export GEMINI_API_KEY='your_key_here'")
    else:
        # Example of how to use your new function:
        speak("Hello, this is the first sentence. It should play and then be deleted.")
        speak("This is the second sentence. I can call this function as many times as I want.")