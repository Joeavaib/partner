import os
from pathlib import Path

def format_path(path_str: str) -> str:
    """
    Format path to be relative to the parent of the current working directory 
    to include the project folder name (e.g. partner/src/...).
    Falls der Pfad außerhalb des Projekts liegt, wird er relativ zum Home-Verzeichnis (if possible) angezeigt.
    """
    try:
        abs_path = Path(path_str).resolve()
        cwd = Path.cwd()
        
        # Versuche Pfad relativ zum Parent des CWD zu machen (inkludiert Projektname)
        try:
            rel_path = os.path.relpath(abs_path, cwd.parent)
            if not rel_path.startswith(".."):
                return rel_path
        except ValueError:
            pass

        # Fallback: Relativ zum Home-Verzeichnis (~/...)
        home = Path.home()
        try:
            if abs_path.is_relative_to(home):
                return "~/" + str(abs_path.relative_to(home))
        except (ValueError, AttributeError):
            pass
            
        return str(abs_path)
    except Exception:
        return str(path_str)
