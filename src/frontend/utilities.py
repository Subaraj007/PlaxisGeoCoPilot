# frontend/utilities.py
import os
import sys

def resource_path(relative_path):
    """Get absolute path to resource for both dev and PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Normal execution - get parent directory of src/frontend
        base_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..'))
    
    full_path = os.path.join(base_path, relative_path)
    
    # Fallback for development if file not found
    if not os.path.exists(full_path) and not getattr(sys, 'frozen', False):
        # Try direct path from project root
        alt_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..', relative_path))
        if os.path.exists(alt_path):
            return alt_path
    
    return full_path