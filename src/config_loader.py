#!/usr/bin/env python3
"""
Config Loader Helper Module
Handles loading configuration from various sources in both development and production
"""

import os
import sys
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Running in normal Python environment
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def get_executable_dir():
    """Get the directory where the executable is located"""
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller executable
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

def resolve_database_path(db_path):
    """Resolve database path based on execution context"""
    if not db_path:
        return db_path
    
    # If it's already an absolute path, return as-is
    if os.path.isabs(db_path):
        return db_path
    
    # Handle relative paths
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller executable
        executable_dir = get_executable_dir()
        
        # Handle different relative path formats
        if db_path.startswith('../data/'):
            # Convert ../data/flet.db to _internal/data/flet.db
            db_name = os.path.basename(db_path)
            resolved_path = os.path.join(executable_dir, "_internal", "data", db_name)
        elif db_path.startswith('data/'):
            # Convert data/flet.db to _internal/data/flet.db
            db_name = os.path.basename(db_path)
            resolved_path = os.path.join(executable_dir, "_internal", "data", db_name)
        elif db_path.startswith('./data/'):
            # Convert ./data/flet.db to _internal/data/flet.db
            db_name = os.path.basename(db_path)
            resolved_path = os.path.join(executable_dir, "_internal", "data", db_name)
        else:
            # Default case - assume it should be in _internal/data
            db_name = os.path.basename(db_path)
            resolved_path = os.path.join(executable_dir, "_internal", "data", db_name)
        
        # Ensure the directory exists
        data_dir = os.path.dirname(resolved_path)
        os.makedirs(data_dir, exist_ok=True)
        
        return resolved_path
    else:
        # Running in development - resolve relative to current directory
        return os.path.abspath(db_path)

def find_config_file():
    """Find config.yaml file in various possible locations"""
    
    config_locations = []
    
    # If running from PyInstaller bundle
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
        config_locations.extend([
            os.path.join(base_path, "config.yaml"),
            os.path.join(base_path, "src", "config.yaml"),
        ])
    
    # Standard development locations
    config_locations.extend([
        "config.yaml",
        "src/config.yaml",
        os.path.join(os.getcwd(), "config.yaml"),
        os.path.join(os.getcwd(), "src", "config.yaml"),
    ])
    
    # Try each location
    for config_path in config_locations:
        if os.path.exists(config_path):
            return config_path
    
    return None

def create_default_config_dict():
    """Create default configuration dictionary"""
    return {
        'database': {
            'host': 'localhost',
            'port': 3306,
            'username': 'root',
            'password': '',
            'database_name': 'geocopilot_db'
        },
        'auth': {
            'enable_auth': True,
            'session_timeout': 3600,
            'max_login_attempts': 3
        },
        'app': {
            'name': 'GeoCoPilot',
            'version': '1.0.0',
            'debug': False,
            'log_level': 'INFO'
        },
        'files': {
            'max_file_size': '50MB',
            'allowed_extensions': ['.xlsx', '.csv', '.ags'],
            'temp_directory': 'temp'
        },
        'plaxis': {
            'auto_connect': True,
            'default_units': 'metric',
            'backup_interval': 300
        },
        'ui': {
            'theme': 'light',
            'window_width': 1200,
            'window_height': 800,
            'show_splash': True
        }
    }

def load_encoded_config():
    """Try to load config from encoded module if available"""
    try:
        import config_encoded
        config_content = config_encoded.get_config()
        config = yaml.safe_load(config_content)
        
        # Apply database path resolution if needed
        if 'database' in config and isinstance(config['database'], dict):
            if 'database' in config['database']:
                original_path = config['database']['database']
                resolved_path = resolve_database_path(original_path)
                config['database']['database'] = resolved_path
                logger.info(f"Resolved database path: {original_path} -> {resolved_path}")
        elif 'database' in config and isinstance(config['database'], str):
            # Handle case where database is directly a string path
            original_path = config['database']
            resolved_path = resolve_database_path(original_path)
            config['database'] = resolved_path
            logger.info(f"Resolved database path: {original_path} -> {resolved_path}")
        
        return config
    except ImportError:
        return None
    except Exception as e:
        logger.error(f"Error loading encoded config: {e}")
        return None

def get_config():
    """Main function to get configuration - tries multiple methods"""
    
    # Method 1: Try encoded config first (for protected builds)
    config = load_encoded_config()
    if config:
        return config
    
    # Method 2: Try regular config file
    config_path = find_config_file()
    if config_path:
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                
                # Apply database path resolution
                if 'database' in config and isinstance(config['database'], dict):
                    if 'database' in config['database']:
                        original_path = config['database']['database']
                        resolved_path = resolve_database_path(original_path)
                        config['database']['database'] = resolved_path
                elif 'database' in config and isinstance(config['database'], str):
                    original_path = config['database']
                    resolved_path = resolve_database_path(original_path)
                    config['database'] = resolved_path
                
                return config
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
    
    # Method 3: Return default config as fallback
    return create_default_config_dict()

# Convenience function for backward compatibility
def load_config_file():
    """Backward compatibility function"""
    return get_config()
