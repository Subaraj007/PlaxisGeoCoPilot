#!/usr/bin/env python3
"""
Enhanced Resource Path Handler for PyInstaller
Ensures all data files are loaded from the correct bundled location
"""

import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def get_base_path():
    """
    Get the base path for resources, works for both development and PyInstaller
    Always returns the correct path where bundled resources are located
    """
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle - use _MEIPASS (the _internal directory)
        base_path = sys._MEIPASS
        logger.debug(f"Using base path from frozen application: {base_path}")
    else:
        # Running in development - use current directory
        base_path = os.path.abspath(".")
        logger.debug(f"Using base path from development: {base_path}")
    
    return base_path

def get_resource_path(relative_path):
    """
    Get absolute path to a resource file
    
    Args:
        relative_path (str): Relative path to the resource (e.g., "data/Input_Data.xlsx")
    
    Returns:
        str: Absolute path to the resource
    """
    base_path = get_base_path()
    
    # Normalize the relative path to use forward slashes
    normalized_path = relative_path.replace('\\', '/')
    
    # Join with base path
    resource_path = os.path.join(base_path, normalized_path)
    
    # Normalize the final path
    resource_path = os.path.normpath(resource_path)
    
    logger.debug(f"Looking for resource: {relative_path} -> {resource_path}")
    logger.debug(f"Resource exists: {os.path.exists(resource_path)}")
    
    return resource_path

def get_data_file_path(filename):
    """
    Get path to a file in the data directory
    
    Args:
        filename (str): Name of the file in the data directory
    
    Returns:
        str: Absolute path to the data file
    """
    return get_resource_path(f"data/{filename}")

def list_data_directory():
    """
    List all files in the data directory for debugging
    
    Returns:
        list: List of files in the data directory
    """
    data_dir = get_resource_path("data")
    if os.path.exists(data_dir):
        files = os.listdir(data_dir)
        logger.debug(f"Files in data directory ({data_dir}): {files}")
        return files
    else:
        logger.warning(f"Data directory does not exist: {data_dir}")
        return []

def ensure_data_file_exists(filename):
    """
    Check if a data file exists and log appropriate messages
    
    Args:
        filename (str): Name of the file to check
    
    Returns:
        tuple: (file_path, exists)
    """
    file_path = get_data_file_path(filename)
    exists = os.path.exists(file_path)
    
    if exists:
        logger.info(f"✓ Found data file: {filename} at {file_path}")
    else:
        logger.error(f"✗ Data file not found: {filename}")
        logger.error(f"  Expected location: {file_path}")
        
        # List available files for debugging
        available_files = list_data_directory()
        if available_files:
            logger.info(f"Available files in data directory: {available_files}")
        else:
            logger.warning("No files found in data directory or directory doesn't exist")
    
    return file_path, exists
