#!/usr/bin/env python3
"""
Advanced source code protection script using multiple techniques
Place this file in your project root directory
"""

import os
import shutil
import subprocess
import sys
import base64
import zlib
from pathlib import Path
import ast
import random
import string

import datetime

# Version info (edit only here)
major = 0
minor = 1
patch = 0
build = 0

def create_version_file():
    build_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # Read template
    with open("product_version.txt.j2", "r") as f:
        template = f.read()
    
    # Write filled version info
    with open("product_version.txt", "w") as f:
        f.write(template.format(
            major=major,
            minor=minor,
            patch=patch,
            build=build,
            build_date=build_date
        ))

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
    dirs_to_clean = ['build', 'dist', 'protected_src']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}...")
            shutil.rmtree(dir_name)

def generate_random_name(length=10):
    """Generate random variable/function names"""
    return ''.join(random.choices(string.ascii_letters, k=length))

def obfuscate_python_code(code):
    """Apply basic obfuscation to Python code"""
    try:
        # Compress and encode
        compressed = zlib.compress(code.encode('utf-8'))
        encoded = base64.b64encode(compressed).decode('utf-8')
        
        # Create obfuscated wrapper
        wrapper = f'''import base64, zlib
exec(zlib.decompress(base64.b64decode('{encoded}')).decode('utf-8'))'''
        
        return wrapper
    except Exception as e:
        print(f"Warning: Could not obfuscate code: {e}")
        return code

def protect_source_files():
    """Protect source files using multiple techniques"""
    print("Applying source code protection...")
    
    protected_dir = "protected_src"
    os.makedirs(protected_dir, exist_ok=True)
    
    source_dirs = ["src/frontend", "src/plaxis"]
    
    for src_dir in source_dirs:
        if os.path.exists(src_dir):
            print(f"Processing {src_dir}...")
            
            rel_path = os.path.relpath(src_dir, "src")
            output_dir = os.path.join(protected_dir, rel_path)
            os.makedirs(output_dir, exist_ok=True)
            
            # Process all files
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    src_file = os.path.join(root, file)
                    rel_file_path = os.path.relpath(src_file, src_dir)
                    dst_file = os.path.join(output_dir, rel_file_path)
                    
                    # Create directory if needed
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    
                    if file.endswith('.py'):
                        try:
                            with open(src_file, 'r', encoding='utf-8') as f:
                                original_code = f.read()
                            
                            # Apply obfuscation
                            protected_code = obfuscate_python_code(original_code)
                            
                            with open(dst_file, 'w', encoding='utf-8') as f:
                                f.write(protected_code)
                            
                            print(f"✓ Protected {src_file}")
                        except Exception as e:
                            print(f"⚠ Could not protect {src_file}: {e}")
                            shutil.copy2(src_file, dst_file)
                    else:
                        # Copy non-Python files
                        shutil.copy2(src_file, dst_file)

def build_executable():
    """Build the executable"""
    print("Building protected executable...")
    result = run_command("pyinstaller build_base64.spec")
    return result is not None

def main():
    """Main build process"""
    print("=== Advanced Source Protection Build ===")
    
    # Clean previous builds
    clean_previous_builds()
    
    # Protect source code
    protect_source_files()

    # Create version file
    create_version_file()
    
    # Build executable
    if build_executable():
        print("\n=== Build Complete ===")
        print("✓ Your protected executable is ready in the 'dist' folder!")
        print("✓ Source code is compressed and encoded")
    else:
        print("\n=== Build Failed ===")

if __name__ == "__main__":
    main()