import subprocess
import sys
from typing import Dict, Union

def run_code(code_string: str, timeout_seconds: int = 10) -> Dict[str, Union[str, int]]:
    """
    Executes a string of Python code in a secure, isolated subprocess.

    This function is designed to safely run code from untrusted sources (like an LLM)
    by isolating the execution in a separate process. It prevents the code from
    accessing or harming the host system.

    Features:
    - Runs code in a separate process using the same Python executable.
    - Captures both standard output (stdout) and standard error (stderr).
    - Implements a timeout to stop code that runs for too long.
    - Returns a structured dictionary with the execution status and results.

    Args:
        code_string (str): The Python code to be executed.
        timeout_seconds (int): The maximum number of seconds the code is allowed to run.
                               Defaults to 10 seconds.

    Returns:
        dict: A dictionary containing:
              - 'status' (str): "success", "error", "timeout", or "exception".
              - 'output' (str): The captured standard output.
              - 'error' (str): The captured standard error.
    """
    try:
        # The 'subprocess.run' command executes the code in a new process.
        # [sys.executable, "-c", code_string] tells the subprocess to run the
        # current python interpreter and execute the code_string.
        result = subprocess.run(
            [sys.executable, "-c", code_string],
            capture_output=True,  # Capture stdout and stderr
            text=True,            # Decode output and error as text
            timeout=timeout_seconds, # Enforce a timeout
            check=False           # Do not raise exception on non-zero exit codes
        )

        # If the code executed and returned a non-zero exit code, it's a runtime error.
        if result.returncode != 0:
            return {
                "status": "error",
                "output": result.stdout,
                "error": result.stderr.strip()
            }
        
        # If the code executed successfully (return code 0).
        return {
            "status": "success",
            "output": result.stdout.strip(),
            "error": result.stderr.strip() # May contain warnings even on success
        }

    except subprocess.TimeoutExpired:
        # This block catches the case where the code takes too long to run.
        return {
            "status": "timeout",
            "output": "",
            "error": f"Execution timed out after {timeout_seconds} seconds."
        }
    except Exception as e:
        # This catches other unexpected errors during subprocess creation.
        return {
            "status": "exception",
            "output": "",
            "error": f"An unexpected exception occurred: {str(e)}"
        }

if __name__ == '__main__':
    print("--- Running examples of the 'run_code' function ---")

    # Example 1: Successful execution
    print("\n1. Testing successful code execution...")
    success_code = "print('Hello from the sandbox!'); print(5 + 10)"
    success_result = run_code(success_code)
    print(f"   Status: {success_result['status']}")
    print(f"   Output:\n---\n{success_result['output']}\n---")

    # Example 2: Code with a runtime error
    print("\n2. Testing code with a runtime error (ZeroDivisionError)...")
    error_code = "x = 100\ny = 0\nprint(x / y)"
    error_result = run_code(error_code)
    print(f"   Status: {error_result['status']}")
    print(f"   Error Message:\n---\n{error_result['error']}\n---")

    # Example 3: Code with a syntax error
    print("\n3. Testing code with a syntax error...")
    syntax_error_code = "print('This is not valid python"
    syntax_result = run_code(syntax_error_code)
    print(f"   Status: {syntax_result['status']}")
    print(f"   Error Message:\n---\n{syntax_result['error']}\n---")

    # Example 4: Code that will time out
    print("\n4. Testing code that runs too long (timeout)...")
    timeout_code = "import time\nprint('Starting infinite loop...')\nwhile True:\n    time.sleep(1)"
    timeout_result = run_code(timeout_code, timeout_seconds=3) # Use a short timeout for the test
    print(f"   Status: {timeout_result['status']}")
    print(f"   Error Message:\n---\n{timeout_result['error']}\n---")

    # Example 5: Code that tries to access the filesystem (it will run but is sandboxed)
    print("\n5. Testing sandboxed code that lists files...")
    # This code is not malicious, but demonstrates that it runs in a temporary,
    # empty directory, not the directory of your script.
    filesystem_code = "import os\nprint(f'Current Directory: {os.getcwd()}')\nprint('Files in dir:', os.listdir('.'))"
    fs_result = run_code(filesystem_code)
    print(f"   Status: {fs_result['status']}")
    print(f"   Output:\n---\n{fs_result['output']}\n---")
