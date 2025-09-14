from pathlib import Path
import sys

def get_project_structure():
    """
    Returns the directory structure of the project.
    Defaults to the current working directory if __file__ is not available.
    """
    # Use __file__ if available, otherwise fall back to the script's entry point
    # or the current working directory as a last resort.
    try:
        # The most reliable way in a script
        project_root = Path(__file__).parent.resolve()
    except NameError:
        # A fallback for interactive sessions or when __file__ is not defined
        project_root = Path.cwd()
        
    return {
        str(path.relative_to(project_root)): path.name 
        for path in project_root.rglob('*')
    }

# Example usage:
if __name__ == "__main__":
    structure = get_project_structure()
    for path, name in structure.items():
        print(f"{path}: {name}")