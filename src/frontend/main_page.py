import os
import sys
import yaml
import logging
import flet as ft
import atexit
import signal
import asyncio
from typing import Callable, Union, Optional, List, Dict, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path

# Patch StreamWriter.__del__ to handle the "Event loop is closed" error
# This is a workaround for a known issue in asyncio

StreamWriter = asyncio.StreamWriter
original_del = getattr(StreamWriter, "__del__", None)


__appname__ = "GeoCoPilot"
__version__ = "1.0.0"
__company__ = "BuildNex AI"
__contact__ = "hello@buildnexai.com"
__license__ = "Proprietary @ BuildNex AI (Pvt) Ltd."


def patched_del(self):
    try:
        original_del(self)
    except RuntimeError:
        # Ignore "Event loop is closed" errors during cleanup
        pass

StreamWriter.__del__ = patched_del

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define resource path function for PyInstaller compatibility
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if getattr(sys, 'frozen', False):
        # Running in bundled mode (as .exe)
        base_path = sys._MEIPASS
        print(f"Using base path from frozen application: {base_path}")
        print(f"Contents of base path: {os.listdir(base_path) if os.path.exists(base_path) else 'Path does not exist'}")
    else:
        # Running in normal Python environment
        # Since main_page.py is in src/frontend/, go up two directories to reach project root
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        print(f"Using base path from development environment: {base_path}")
    
    full_path = os.path.join(base_path, relative_path)
    print(f"Looking for resource: {relative_path} -> {full_path}")
    print(f"Resource exists: {os.path.exists(full_path)}")
    
    return full_path

# Ensure project root is in sys.path for imports
project_root = resource_path('')
src_path = os.path.join(project_root, 'src')

if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Now import your modules
from frontend.form_app import FormApp
from frontend.database_config import DatabaseConfig
from frontend.schema import ensure_database_ready
from frontend.terminal_logger import setup_terminal_logging

# Global app instance and logger
app_instance = None
terminal_logger = None

# Define minimum and default application dimensions
MIN_WIDTH = 800  # Minimum width in pixels
MIN_HEIGHT = 600  # Minimum height in pixels
DEFAULT_WIDTH = 1070.6  # Default width in pixels
DEFAULT_HEIGHT = 800.0  # Default height in pixels

def cleanup_resources():
    """Clean up resources before application exit"""
    global terminal_logger
    
    logging.info("Performing application cleanup...")
    
    # Stop terminal logging
    if terminal_logger:
        terminal_logger.stop()
        print(f"Log file saved at: {terminal_logger.get_log_path()}")
    
    # Add any cleanup code here
    # For example, close database connections

# Register cleanup function to be called on program exit
atexit.register(cleanup_resources)

def load_config() -> DatabaseConfig:
    """
    Load database configuration from config.yaml
      
    Returns:
        DatabaseConfig: Configured database settings
    """
    # Try multiple possible locations for config.yaml
    possible_config_paths = [
        resource_path('src/config.yaml'),  # Bundled location
        resource_path('config.yaml'),      # Alternative bundled location
        os.path.join(os.path.dirname(__file__), '..', 'config.yaml'),  # Dev location
        'src/config.yaml',  # Fallback
        'config.yaml'       # Root fallback
    ]
    
    config_path = None
    config = None
    
    for path in possible_config_paths:
        print(f"Trying config file at: {path}")
        if os.path.exists(path):
            config_path = path
            print(f"Found config file at: {config_path}")
            break
    
    if not config_path:
        # Create a default config if none found
        logging.warning("No config file found, creating default configuration")
        config = {
            'database': {
                'database': 'data/flet.db'
            }
        }
    else:
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                print(f"Successfully loaded config: {config}")
        except Exception as e:
            logging.error(f"Error reading config file {config_path}: {e}")
            raise
    
    # Get the database path from config
    db_path = config['database']['database']
    
    # **FIX: Resolve relative paths properly**
    if not os.path.isabs(db_path):
        if getattr(sys, 'frozen', False):
            # In bundled mode, resolve relative to the executable's directory
            exe_dir = os.path.dirname(sys.executable)
            db_path = os.path.normpath(os.path.join(exe_dir, db_path))
        else:
            # In development mode, resolve relative to project root
            # config.yaml is in project_root/src/, and db path is ../data/flet.db
            # So we need to resolve from the config file's directory
            if config_path:
                config_dir = os.path.dirname(os.path.abspath(config_path))
                db_path = os.path.normpath(os.path.join(config_dir, db_path))
            else:
                # Fallback to resource_path
                db_path = resource_path(db_path)
    
    # Ensure absolute path
    db_path = os.path.abspath(db_path)
    
    # Print detailed path information
    print(f"=" * 70)
    print(f"DATABASE PATH RESOLUTION")
    print(f"=" * 70)
    print(f"Config DB path: {config['database']['database']}")
    print(f"Resolved DB path: {db_path}")
    print(f"Database exists: {os.path.exists(db_path)}")
    print(f"=" * 70)
    
    # Ensure the directory exists
    db_dir = os.path.dirname(db_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        print(f"Created database directory: {db_dir}")
    else:
        print(f"Database directory exists: {db_dir}")
        # List existing files in the directory
        try:
            files = os.listdir(db_dir)
            print(f"Files in database directory: {files}")
        except Exception as e:
            print(f"Could not list directory contents: {e}")
    
    # Ensure database is ready before proceeding
    if not ensure_database_ready(db_path):
        logging.error("Failed to prepare database. Exiting.")
        raise RuntimeError("Database initialization failed")
    
    # Create DatabaseConfig
    db_config = DatabaseConfig(
        database=db_path
    )
    return db_config
 
def safe_exit(signum=None, frame=None):
    """Handle exit signals gracefully"""
    logging.info("Exit signal received, shutting down...")
    cleanup_resources()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, safe_exit)
signal.signal(signal.SIGTERM, safe_exit)

def main():
    """
    Main application entry point
    """
    global app_instance, terminal_logger
    
    try:
        # ✅ START TERMINAL LOGGING FIRST - This captures everything after this line
        terminal_logger = setup_terminal_logging()
        print("Starting application...")
        
        # Debug: Print current working directory and sys.path
        print(f"Current working directory: {os.getcwd()}")
        print(f"Script location: {__file__}")
        print(f"Frozen: {getattr(sys, 'frozen', False)}")
        if getattr(sys, 'frozen', False):
            print(f"_MEIPASS: {sys._MEIPASS}")
            print(f"Executable: {sys.executable}")
        
        # Load configuration
        db_config = load_config()
        print(f"Database config loaded successfully: {db_config.database}")
        
        # Create app instance
        app_instance = FormApp(db_config)
        
        def app_initialize(page: ft.Page):
            # Set initial window size and properties
            page.window_width = DEFAULT_WIDTH
            page.window_height = DEFAULT_HEIGHT
            page.window_min_width = MIN_WIDTH
            page.window_min_height = MIN_HEIGHT
            page.update()
            
            # Handle window resize event
            def on_window_resize(e):
                # The event data in Flet is passed as a string, not a dictionary
                # We need to convert the width and height to integers
                try:
                    # Access width and height directly from the page object instead
                    current_width = page.window_width
                    current_height = page.window_height
        
                    # Enforce minimum dimensions
                    if current_width < MIN_WIDTH or current_height < MIN_HEIGHT:
                        # Reset to minimum dimensions if user attempts to go smaller
                        page.window_width = max(current_width, MIN_WIDTH)
                        page.window_height = max(current_height, MIN_HEIGHT)
                        page.update()
        
                    logging.info(f"Window resized to: {page.window_width}x{page.window_height}")
                except Exception as ex:
                    logging.error(f"Error in resize handler: {ex}")
            
            # Register resize event handler
            page.on_resize = on_window_resize
            
            # Setup proper exit handling
            def handle_page_close(e):
                logging.info("Window closing, cleaning up...")
                cleanup_resources()
                page.window_destroy()
            
            page.on_close = handle_page_close
            
            # Handle missing files more gracefully
            try:
                app_instance.initialize(page)
            except FileNotFoundError as e:
                logging.warning(f"File not found: {e}")
                page.add(
                    ft.Column([
                        ft.Text("Required files are missing", size=20, weight="bold"),
                        ft.Text(f"Error: {str(e)}"),
                        ft.ElevatedButton("Try Again", 
                                         on_click=lambda _: app_instance.initialize(page))
                    ])
                )
                page.update()
        
        # Start the application
        ft.app(target=app_initialize)
        
        # Application has ended normally
        print("Application ended normally")
                
    except Exception as e:
        logging.error(f"Application startup failed: {e}")
        import traceback
        logging.error(traceback.format_exc())
    finally:
        # ✅ ALWAYS stop logging - this ensures the file is saved
        print("Cleaning up and saving log file...")
        cleanup_resources()

if __name__ == "__main__":
    main()