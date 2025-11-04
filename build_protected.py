#!/usr/bin/env python3
"""
Hybrid PyArmor + Base64 Source Protection Build Script
Protects critical files with PyArmor, others with Base64 encoding
"""

import os
import shutil
import subprocess
import sys
import base64
import zlib
import random
import string
import datetime
from pathlib import Path

# Version information
MAJOR = 0
MINOR = 1
PATCH = 0
BUILD = 0

# Critical files to protect with PyArmor (use relative paths from src directory)
CRITICAL_FILES = [
    "plaxis/Main.py",
    "frontend/main_page.py",
    "frontend/auth_server_handler_singleton.py"
]

# Sensitive non-Python files to protect with custom encoding
SENSITIVE_CONFIG_FILES = [
    "config.yaml"
]

# Custom icon path
CUSTOM_ICON_PATH = r"C:\Users\Hasini\OneDrive\Desktop\Last_Intern\geo_co_pilot\Buildnex_AI_1.png"

def create_default_config():
    """Create a default config.yaml file if it doesn't exist"""
    default_config_content = """# Default Configuration File
# Database Configuration
database:
  host: "localhost"
  port: 3306
  username: "root"
  password: ""
  database_name: "geocopilot_db"
  
# Authentication Settings
auth:
  enable_auth: true
  session_timeout: 3600
  max_login_attempts: 3

# Application Settings
app:
  name: "GeoCoPilot"
  version: "1.0.0"
  debug: false
  log_level: "INFO"
  
# File Processing Settings
files:
  max_file_size: 50MB
  allowed_extensions: [".xlsx", ".csv", ".ags"]
  temp_directory: "temp"
  
# Plaxis Integration
plaxis:
  auto_connect: true
  default_units: "metric"
  backup_interval: 300
  
# UI Settings
ui:
  theme: "light"
  window_width: 1200
  window_height: 800
  show_splash: true
"""
    
    return default_config_content

def update_config_for_executable():
    """Update config.yaml to use the correct database path for executable"""
    config_path = os.path.join("src", "config.yaml")
    
    if not os.path.exists(config_path):
        print(f"⚠️  Config file not found at {config_path}")
        return False
    
    try:
        # Read the original config
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        # Create a backup
        backup_path = config_path + ".backup"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print(f"✓ Created config backup at {backup_path}")
        
        # Update the database path for executable
        # Change ../data/flet.db to point to _internal/data/flet.db
        updated_content = config_content.replace(
            "database: ../data/flet.db",
            "database: _internal/data/flet.db"
        )
        
        # Also handle other possible variations
        updated_content = updated_content.replace(
            "database: data/flet.db",
            "database: _internal/data/flet.db"
        )
        
        # Write the updated config
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print("✓ Updated config.yaml database path for executable build")
        return True
        
    except Exception as e:
        print(f"✗ Failed to update config: {str(e)}")
        return False

def restore_config_backup():
    """Restore the original config from backup"""
    config_path = os.path.join("src", "config.yaml")
    backup_path = config_path + ".backup"
    
    if os.path.exists(backup_path):
        try:
            shutil.copy2(backup_path, config_path)
            os.remove(backup_path)
            print("✓ Restored original config.yaml")
        except Exception as e:
            print(f"⚠️  Could not restore config backup: {str(e)}")

def ensure_config_exists():
    """Ensure config.yaml exists in the correct location"""
    config_paths = [
        "src/config.yaml",
        "config.yaml",
        os.path.join(os.getcwd(), "src", "config.yaml"),
        os.path.join(os.getcwd(), "config.yaml")
    ]
    
    # Check if config exists in any expected location
    existing_config = None
    for path in config_paths:
        if os.path.exists(path):
            existing_config = path
            print(f"✓ Found existing config at: {path}")
            break
    
    # If no config found, create default one
    if not existing_config:
        print("⚠️  No config file found, creating default configuration...")
        
        # Ensure src directory exists
        src_dir = "src"
        os.makedirs(src_dir, exist_ok=True)
        
        # Create default config
        config_path = os.path.join(src_dir, "config.yaml")
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(create_default_config())
        
        print(f"✓ Created default config at: {config_path}")
        return config_path
    
    # If config exists but not in src/, copy it there
    target_config = os.path.join("src", "config.yaml")
    
    # Normalize paths for comparison to avoid issues with different path separators
    existing_config_abs = os.path.abspath(existing_config)
    target_config_abs = os.path.abspath(target_config)
    
    if existing_config_abs != target_config_abs:
        os.makedirs("src", exist_ok=True)
        try:
            shutil.copy2(existing_config, target_config)
            print(f"✓ Copied config from {existing_config} to {target_config}")
        except (PermissionError, shutil.SameFileError) as e:
            print(f"⚠️  Could not copy config file: {str(e)}")
            print(f"Using existing config at: {existing_config}")
            return existing_config
    else:
        print(f"✓ Config already in correct location: {existing_config}")
    
    return target_config

def create_version_file():
    """Create version file with build information"""
    build_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    version_content = f"""# Application Version
major = {MAJOR}
minor = {MINOR}
patch = {PATCH}
build = {BUILD}
build_date = "{build_date}"
"""
    
    with open("version.py", "w") as f:
        f.write(version_content)
    print("✓ Created version.py")

def run_command(cmd, cwd=None):
    """Run a command and handle errors"""
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, cwd=cwd, 
                              capture_output=True, text=True)
        print(f"✓ Success: {cmd}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"✗ Error running: {cmd}")
        print(f"Error output: {e.stderr}")
        return None

def clean_previous_builds():
    """Clean previous builds and obfuscated code"""
    dirs_to_clean = ['build', 'dist', 'protected_src', 'pyarmor_runtime', 'pyarmor_temp']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}...")
            shutil.rmtree(dir_name)

def check_pyarmor_installation():
    """Check if PyArmor is installed"""
    result = run_command("pyarmor --version")
    if result is None:
        print("PyArmor is not installed. Installing...")
        install_result = run_command("pip install pyarmor")
        if install_result is None:
            print("Failed to install PyArmor. Using base64 fallback for all files")
            return False
        print("✓ PyArmor installed successfully")
    else:
        print("✓ PyArmor is already installed")
    return True

def get_pyarmor_version():
    """Get PyArmor version to determine correct syntax"""
    result = run_command("pyarmor --version")
    if result:
        version_line = result.stdout.strip()
        print(f"PyArmor version: {version_line}")
        if "trial" in version_line.lower():
            print("⚠️  WARNING: Using PyArmor trial version with limitations")
        if "8." in version_line:
            return "8"
        elif "7." in version_line:
            return "7"
    return "unknown"

def base64_encode_file(input_path, output_path):
    """Apply base64 encoding to a file"""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            original_code = f.read()
        
        # Compress and encode the source code
        compressed = zlib.compress(original_code.encode('utf-8'))
        encoded = base64.b64encode(compressed).decode('utf-8')
        
        # Create wrapper that decodes and executes the original code
        wrapper = f"""import base64, zlib
exec(zlib.decompress(base64.b64decode('{encoded}')).decode('utf-8'))"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(wrapper)
        
        return True
    except Exception as e:
        print(f"✗ Base64 encoding failed for {input_path}: {str(e)}")
        return False

def encode_config_file(input_path, output_path):
    """Encode configuration files with proper path handling"""
    try:
        # Verify input file exists
        if not os.path.exists(input_path):
            print(f"⚠️  Config file not found at {input_path}")
            return False
            
        with open(input_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # Compress and encode the configuration
        compressed = zlib.compress(original_content.encode('utf-8'))
        encoded = base64.b64encode(compressed).decode('utf-8')
        
        # Create a Python module that returns the decoded content
        wrapper = f"""import base64, zlib

def get_config():
    '''Returns the decoded configuration content'''
    return zlib.decompress(base64.b64decode('{encoded}')).decode('utf-8')

# For backward compatibility, you can also access as a string
CONFIG_CONTENT = get_config()
"""
        
        # Save encoded config directly to protected_src root directory
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        py_output_path = os.path.join("protected_src", f"{base_name}_encoded.py")
        
        with open(py_output_path, 'w', encoding='utf-8') as f:
            f.write(wrapper)
        
        print(f"✓ Config file encoded: {input_path} -> {py_output_path}")
        return True
    except Exception as e:
        print(f"✗ Config encoding failed for {input_path}: {str(e)}")
        return False

def protect_with_pyarmor(input_path, output_dir):
    """Protect a file with PyArmor"""
    version = get_pyarmor_version()
    
    # Create PyArmor command based on version
    if version == "8":
        cmd = f"pyarmor gen --output {output_dir} {input_path}"
    elif version == "7":
        cmd = f"pyarmor obfuscate --output {output_dir} {input_path}"
    else:
        cmd = f"pyarmor gen --output {output_dir} {input_path}"
    
    result = run_command(cmd)
    return result is not None

def copy_pyarmor_runtime(source_dir, target_dir):
    """Copy PyArmor runtime files to protected directory"""
    runtime_dirs = ["pyarmor_runtime_000000", "pyarmor_runtime"]
    
    for runtime_dir in runtime_dirs:
        source_path = os.path.join(source_dir, runtime_dir)
        if os.path.exists(source_path):
            target_path = os.path.join(target_dir, runtime_dir)
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
            shutil.copytree(source_path, target_path)
            print(f"✓ Copied PyArmor runtime: {runtime_dir}")
            return runtime_dir
    
    print("⚠️  PyArmor runtime not found")
    return None

def create_config_loader():
    """Create the config_loader.py helper module with path resolution"""
    config_loader_content = '''#!/usr/bin/env python3
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
'''
    
    # Write to both src and protected_src directories
    for directory in ["src", "protected_src"]:
        os.makedirs(directory, exist_ok=True)
        config_loader_path = os.path.join(directory, "config_loader.py")
        with open(config_loader_path, 'w', encoding='utf-8') as f:
            f.write(config_loader_content)
        print(f"✓ Created config_loader.py in {directory}")

def ensure_data_files():
    """Ensure all required data files exist and are in the right location"""
    data_dir = "data"
    required_files = ["Input_Data.xlsx", "Steel_member_properties.xlsx"]
    
    # Create data directory if it doesn't exist
    os.makedirs(data_dir, exist_ok=True)
    
    # Check if each required file exists
    for file_name in required_files:
        file_path = os.path.join(data_dir, file_name)
        if not os.path.exists(file_path):
            print(f"⚠️  Required data file not found: {file_path}")
            # Try to find it in other locations
            possible_locations = [
                os.path.join("src", data_dir, file_name),
                os.path.join("..", data_dir, file_name),
                os.path.join(os.getcwd(), "..", data_dir, file_name),
            ]
            
            found = False
            for location in possible_locations:
                if os.path.exists(location):
                    try:
                        shutil.copy2(location, file_path)
                        print(f"✓ Copied {file_name} from {location} to {file_path}")
                        found = True
                        break
                    except Exception as e:
                        print(f"✗ Failed to copy {file_name}: {str(e)}")
            
            if not found:
                print(f"✗ Critical error: {file_name} not found anywhere!")
                return False
    
    print("✓ All required data files are available")
    return True

def protect_source_files():
    """Protect source files using hybrid approach"""
    print("Applying hybrid source protection...")
    
    protected_dir = "protected_src"
    os.makedirs(protected_dir, exist_ok=True)
    
    # Create config loader helper
    create_config_loader()
    
    # Ensure data files exist
    if not ensure_data_files():
        print("✗ Data files validation failed")
        return False, None
    
    # Temporary directory for PyArmor operations
    temp_dir = "pyarmor_temp"
    os.makedirs(temp_dir, exist_ok=True)
    
    pyarmor_used = False
    runtime_dir_name = None
    
    # First, ensure config file exists and handle config files
    config_path = ensure_config_exists()
    
    for config_file in SENSITIVE_CONFIG_FILES:
        config_full_path = os.path.join("src", config_file)
        if os.path.exists(config_full_path):
            print(f"Encoding config file: {config_full_path}")
            encode_config_file(config_full_path, config_full_path)
        else:
            print(f"⚠️  Config file not found: {config_full_path}")
    
    # Verify src directory exists
    if not os.path.exists("src"):
        print("✗ Source directory 'src' not found!")
        return False, None
    
    # Process all source files
    for root, dirs, files in os.walk("src"):
        for file in files:
            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(root, "src")
            dst_dir = os.path.join(protected_dir, rel_path)
            os.makedirs(dst_dir, exist_ok=True)
            dst_path = os.path.join(dst_dir, file)
            
            # Get relative path from src for comparison
            file_rel_path = os.path.relpath(src_path, "src").replace(os.sep, "/")
            
            # Process Python files
            if file.endswith('.py'):
                # Check if file is critical (using relative path)
                if file_rel_path in CRITICAL_FILES:
                    print(f"Protecting critical file: {src_path} (matched: {file_rel_path})")
                    
                    # Try PyArmor first
                    pyarmor_success = protect_with_pyarmor(src_path, temp_dir)
                    
                    if pyarmor_success:
                        pyarmor_used = True
                        
                        # Find the protected file in temp directory
                        protected_file = None
                        for f in os.listdir(temp_dir):
                            if f.endswith('.py') and not f.startswith('pyarmor'):
                                protected_file = os.path.join(temp_dir, f)
                                break
                        
                        if protected_file:
                            # Move to protected directory
                            shutil.move(protected_file, dst_path)
                            print(f"✓ PyArmor protected: {src_path}")
                            
                            # Copy runtime if not already copied
                            if not runtime_dir_name:
                                runtime_dir_name = copy_pyarmor_runtime(temp_dir, protected_dir)
                        else:
                            print(f"⚠️  PyArmor output not found for {src_path}, using base64")
                            base64_encode_file(src_path, dst_path)
                    else:
                        print(f"⚠️  PyArmor failed for {src_path}, using base64")
                        base64_encode_file(src_path, dst_path)
                else:
                    # Non-critical files get base64 encoding
                    print(f"Base64 encoding: {src_path}")
                    base64_encode_file(src_path, dst_path)
            
            # Skip config files (already handled above)
            elif file in SENSITIVE_CONFIG_FILES:
                continue  # Already processed above
            
            else:
                # Copy non-Python, non-config files directly
                shutil.copy2(src_path, dst_path)
    
    # Clean up temporary directory
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    return pyarmor_used, runtime_dir_name

def create_hybrid_spec(runtime_dir_name=None):
    """Create PyInstaller spec file with proper config handling"""
    print("Creating hybrid spec file...")
    
    # Find entry point in protected source - try critical files first
    entry_point = None
    critical_entry_candidates = [
        "frontend/main_page.py",
        "plaxis/Main.py",
        "frontend/auth_server_handler_singleton.py"
    ]
    
    for candidate in critical_entry_candidates:
        candidate_path = os.path.join("protected_src", candidate.replace("/", os.sep))
        if os.path.exists(candidate_path):
            entry_point = candidate_path
            break
    
    if not entry_point:
        print("⚠️  No critical entry point found, searching for any .py file")
        for root, dirs, files in os.walk("protected_src"):
            for file in files:
                if file.endswith('.py'):
                    entry_point = os.path.join(root, file)
                    break
            if entry_point:
                break
    
    if not entry_point:
        print("✗ No entry point found in protected_src")
        return False
    
    print(f"Using entry point: {entry_point}")
    
    # Build datas list with proper path formatting
    datas_entries = []
    
    # Always include the original config.yaml file for runtime access
    config_path = os.path.join('src', 'config.yaml')
    if os.path.exists(config_path):
        datas_entries.append(f"(os.path.join(project_root, 'src', 'config.yaml'), '.')")
        datas_entries.append(f"(os.path.join(project_root, 'src', 'config.yaml'), 'src')")
        print(f"✓ Including config.yaml in bundle")
    
    # Also include encoded config if it exists
    config_encoded_path = os.path.join('protected_src', 'config_encoded.py')
    if os.path.exists(config_encoded_path):
        datas_entries.append(f"(os.path.join(project_root, 'protected_src', 'config_encoded.py'), '.')")
        print(f"✓ Including config_encoded.py in bundle")
    
    # Data files - ensure they're included in the _internal directory
    data_dir = 'data'
    if os.path.exists(data_dir):
        datas_entries.append(f"(os.path.join(project_root, 'data'), 'data')")
        print(f"✓ Including data directory in bundle")
    
    # Assets directory
    assets_dir = 'assets'
    if os.path.exists(assets_dir):
        datas_entries.append(f"(os.path.join(project_root, 'assets'), 'assets')")
        print(f"✓ Including assets directory in bundle")
    
    # Include PyArmor runtime if it exists
    if runtime_dir_name:
        runtime_path = os.path.join('protected_src', runtime_dir_name)
        if os.path.exists(runtime_path):
            datas_entries.append(f"(os.path.join(project_root, 'protected_src', '{runtime_dir_name}'), '{runtime_dir_name}')")
            print(f"✓ Including PyArmor runtime in bundle")
    
    # Format datas list with proper syntax
    datas_str = ",\n        ".join(datas_entries) if datas_entries else ""
    
    # Convert entry point to use forward slashes for consistency
    entry_point_normalized = entry_point.replace(os.sep, '/')
    
    # Handle icon path - use custom icon if available
    icon_path = None
    if os.path.exists(CUSTOM_ICON_PATH):
        icon_path = CUSTOM_ICON_PATH
        print(f"✓ Using custom icon: {CUSTOM_ICON_PATH}")
    else:
        # Fallback to default icon in assets folder
        default_icon = os.path.join('assets', 'app.ico')
        if os.path.exists(default_icon):
            icon_path = default_icon
            print(f"✓ Using default icon: {default_icon}")
        else:
            print("⚠️  No icon file found, executable will use default icon")
    
    # Add config_loader to hidden imports
    hidden_imports = [
        'config_loader',  # Added config loader helper
        'config_encoded',  # Added for encoded config support
        'tkinter', 'tkinter.filedialog', 'mysql', 'mysql.connector',
        'flet', 'sqlite3', 'pandas', 'openpyxl', 'yaml', 'scipy', 'numpy',
        'asyncio', 'asyncio.windows_events', 'apscheduler', 'requests',
        'apscheduler.schedulers', 'apscheduler.schedulers.base',
        'apscheduler.triggers.date', 'plxscripting', 'plxscripting.easy',
        'xlsxwriter', 'openpyxl', 'base64', 'zlib',
        'plaxis.Main', 'plaxis.ConnectToPlaxis', 'plaxis.FlowCondition',
        'plaxis.Materials', 'plaxis.ModelInfo', 'plaxis.Structures',
        'pyarmor_runtime_000000', 'pyarmor_runtime', 'pytransform',
        'frontend.form_app', 'frontend.database_config', 'frontend.schema',
        'frontend.auth_manager', 'frontend.auth_server_handler',
        'frontend.auth_server_handler_singleton', 'frontend.borehole_section',
        'frontend.create_model', 'frontend.create_ui', 'frontend.csv_template_handler',
        'frontend.database_connection', 'frontend.database_operations',
        'frontend.excavation_section', 'frontend.file_importer', 'frontend.form_manager',
        'frontend.form_section', 'frontend.full_import', 'frontend.gcp_file_handler',
        'frontend.geometry_section', 'frontend.import_data_handler', 'frontend.login_screen',
        'frontend.project_info_section', 'frontend.sequence_construct_section',
        'frontend.soil_db_handler', 'frontend.user_profile', 'frontend.utilities',
        'frontend.ags_data_handler',    'frontend.wall_details_handler' ,'frontend.lineload_details_handler' ,'frontend.terminal_logger'

    ]
    
    # Format hidden imports
    hidden_imports_str = ",\n        ".join([f"'{imp}'" for imp in hidden_imports])
    
    # Format icon path for spec file
    icon_spec = f"icon=r'{icon_path}'," if icon_path else "icon=None,"
    
    spec_content = f"""# -*- mode: python -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os
import sys

block_cipher = None
project_root = os.path.abspath('.')

a = Analysis(
    ['{entry_point_normalized}'],
    pathex=[
        project_root, 
        'protected_src',
        'protected_src/frontend',
        'protected_src/plaxis',
        'src',
        'src/frontend', 
        'src/plaxis'
    ],
    datas=[
        {datas_str}
    ],
    hiddenimports=[
        {hidden_imports_str},
        *collect_submodules('flet_core'),
        *collect_submodules('flet_async'),
        *collect_submodules('apscheduler')
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GeoCoPilot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    {icon_spec}
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='GeoCoPilot',
    strip=False,
    upx=True,
    upx_exclude=[],
)
"""
    
    with open('build_hybrid.spec', 'w') as f:
        f.write(spec_content)
    
    print("✓ Created build_hybrid.spec")
    return True

def build_executable():
    """Build the executable with PyInstaller"""
    print("Building executable with PyInstaller...")
    result = run_command("pyinstaller build_hybrid.spec")
    return result is not None

def validate_environment():
    """Validate that all required directories and files exist"""
    print("Validating build environment...")
    
    issues = []
    
    # Check if we're in the right directory
    if not os.path.exists("src"):
        issues.append("❌ 'src' directory not found in current working directory")
        print(f"Current working directory: {os.getcwd()}")
        print("Available directories:", [d for d in os.listdir('.') if os.path.isdir(d)])
    
    # List all Python files in src to help debug
    if os.path.exists("src"):
        print("Python files found in src:")
        for root, dirs, files in os.walk("src"):
            for file in files:
                if file.endswith('.py'):
                    rel_path = os.path.relpath(os.path.join(root, file), "src").replace(os.sep, "/")
                    print(f"  - {rel_path}")
    
    if issues:
        for issue in issues:
            print(issue)
        return False
    
    return True

def post_build_cleanup():
    """Clean up after build and restore original config"""
    print("Performing post-build cleanup...")
    
    # Restore original config
    restore_config_backup()
    
    # Clean up temporary files
    temp_files = ['build_hybrid.spec', 'version.py']
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                print(f"✓ Cleaned up {temp_file}")
            except Exception as e:
                print(f"⚠️  Could not remove {temp_file}: {str(e)}")

def main():
    """Main build process"""
    print("=== Hybrid PyArmor + Base64 Protected Build ===")
    print(f"Current working directory: {os.getcwd()}")
    
    # Validate environment first
    if not validate_environment():
        print("\n✗ Environment validation failed. Please check your directory structure.")
        print("Make sure you're running this script from the project root directory.")
        sys.exit(1)
    
    # Clean previous builds
    clean_previous_builds()
    
    # Create version file
    create_version_file()
    
    # Ensure config file exists
    ensure_config_exists()
    
    # Update config for executable (this modifies the database path)
    if not update_config_for_executable():
        print("⚠️  Could not update config for executable, continuing with original")
    
    # Check PyArmor installation
    pyarmor_available = check_pyarmor_installation()
    
    # Protect source files
    pyarmor_used = False
    runtime_dir_name = None
    if pyarmor_available:
        result = protect_source_files()
        if result:
            pyarmor_used, runtime_dir_name = result
        else:
            print("✗ Source protection failed")
            post_build_cleanup()
            sys.exit(1)
    
    # Create spec file
    if not create_hybrid_spec(runtime_dir_name):
        print("✗ Spec file creation failed")
        post_build_cleanup()
        sys.exit(1)
    
    # Build executable
    build_success = build_executable()
    
    # Always perform cleanup
    post_build_cleanup()
    
    if build_success:
        print("\n✓ Build completed successfully!")
        print("Protected executable is in the 'dist' directory")
        print("✓ Database path configured for executable environment")
        print("✓ flet.db will be created in: dist/GeoCoPilot/_internal/data/")
        if pyarmor_used:
            print("✓ Critical files were protected with PyArmor")
        print("✓ Other files were protected with Base64 encoding")
        print("✓ Config files were encoded with custom protection")
    else:
        print("\n✗ Build failed")
        sys.exit(1)

if __name__ == "__main__":
    main()