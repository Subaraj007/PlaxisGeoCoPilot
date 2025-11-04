#!/usr/bin/env python3
"""
Improved PyArmor + PyInstaller source code protection build script
Handles PyArmor trial license limitations and provides partial_protected options
Place this file in your project root directory
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

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
        print(f"Standard output: {e.stdout}")
        return None

def clean_previous_builds():
    """Clean previous builds and obfuscated code"""
    dirs_to_clean = ['build', 'dist', 'pyarmor_obfuscated']
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
            print("Failed to install PyArmor. Please install manually: pip install pyarmor")
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
        # Check if it's trial version
        if "trial" in version_line.lower():
            print("⚠️  WARNING: Using PyArmor trial version with limitations")
        # Extract version number
        if "8." in version_line:
            return "8"
        elif "7." in version_line:
            return "7"
    return "unknown"

def get_critical_files():
    """Get list of critical files to obfuscate first (for trial license)"""
    critical_files = [
        "main_page.py",
        "__init__.py",
        "app.py",
        "main.py"
    ]
    
    found_files = []
    for root, dirs, files in os.walk("src"):
        for file in files:
            if file in critical_files:
                rel_path = os.path.relpath(os.path.join(root, file), "src")
                found_files.append(rel_path)
    
    print(f"Critical files found: {found_files}")
    return found_files

def obfuscate_critical_files_only():
    """Obfuscate only critical files due to trial license limitations"""
    print("Obfuscating critical files only (trial license workaround)...")
    
    # Create obfuscated directory structure
    obfuscated_dir = "pyarmor_obfuscated"
    os.makedirs(obfuscated_dir, exist_ok=True)
    
    # Copy entire src structure first
    src_dest = os.path.join(obfuscated_dir, "src")
    if os.path.exists("src"):
        shutil.copytree("src", src_dest, dirs_exist_ok=True)
        print("✓ Copied source structure")
    
    # Get critical files
    critical_files = get_critical_files()
    
    if not critical_files:
        print("⚠️  No critical files found, proceeding with full directory")
        return obfuscate_with_pyarmor()
    
    # Try to obfuscate individual critical files
    success_count = 0
    for critical_file in critical_files:
        file_path = os.path.join("src", critical_file)
        if os.path.exists(file_path):
            # Create individual obfuscation command
            output_dir = os.path.join(obfuscated_dir, "temp_" + critical_file.replace("/", "_").replace("\\", "_"))
            pyarmor_cmd = f"pyarmor gen --output {output_dir} {file_path}"
            
            result = run_command(pyarmor_cmd)
            if result is not None:
                success_count += 1
                print(f"✓ Obfuscated {critical_file}")
                
                # Move obfuscated file to correct location
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        if file.endswith('.py'):
                            src_file = os.path.join(root, file)
                            # Determine destination
                            rel_path = os.path.relpath(src_file, output_dir)
                            if rel_path.startswith("src"):
                                rel_path = rel_path[4:]  # Remove 'src/' prefix
                            dest_file = os.path.join(src_dest, rel_path)
                            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                            shutil.copy2(src_file, dest_file)
                            print(f"  → Moved to {dest_file}")
                
                # Clean up temp directory
                shutil.rmtree(output_dir)
            else:
                print(f"✗ Failed to obfuscate {critical_file}")
    
    if success_count > 0:
        print(f"✓ Successfully obfuscated {success_count} critical files")
        return True
    else:
        print("✗ Failed to obfuscate any critical files")
        return False

def obfuscate_with_pyarmor():
    """Obfuscate source code using PyArmor"""
    print("Attempting full directory obfuscation with PyArmor...")
    
    # Create obfuscated directory
    obfuscated_dir = "pyarmor_obfuscated"
    
    # Get PyArmor version to use correct syntax
    version = get_pyarmor_version()
    
    if version == "8":
        # PyArmor 8.x syntax
        pyarmor_cmd = f"pyarmor gen --output {obfuscated_dir} src"
    elif version == "7":
        # PyArmor 7.x syntax
        pyarmor_cmd = f"pyarmor obfuscate --output {obfuscated_dir} --recursive src"
    else:
        # Try the basic command that should work with most versions
        print("Unknown PyArmor version, trying basic command...")
        pyarmor_cmd = f"pyarmor gen --output {obfuscated_dir} src"
    
    result = run_command(pyarmor_cmd)
    if result is None:
        # If gen fails, try the older obfuscate command
        print("Trying alternative PyArmor command...")
        pyarmor_cmd = f"pyarmor obfuscate --output {obfuscated_dir} --recursive src"
        result = run_command(pyarmor_cmd)
        
        if result is None:
            print("Full obfuscation failed, trying critical files only...")
            return obfuscate_critical_files_only()
    
    print("✓ Source code obfuscated with PyArmor")
    return True

def find_main_entry_point():
    """Find the correct path to main entry point in obfuscated folder"""
    print("Searching for main entry point in obfuscated folder...")
    
    # Possible entry point names
    entry_candidates = ["main_page.py", "main.py", "app.py"]
    
    obfuscated_dir = "pyarmor_obfuscated"
    if os.path.exists(obfuscated_dir):
        print(f"Contents of {obfuscated_dir}:")
        
        found_entry = None
        for root, dirs, files in os.walk(obfuscated_dir):
            level = root.replace(obfuscated_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            
            for file in files:
                print(f"{subindent}{file}")
                if file in entry_candidates:
                    full_path = os.path.join(root, file)
                    print(f"Found potential entry point: {full_path}")
                    if not found_entry:  # Use the first one found
                        found_entry = full_path
        
        if found_entry:
            return found_entry
        
        # If no exact match, look for any Python file with 'main' in the name
        for root, dirs, files in os.walk(obfuscated_dir):
            for file in files:
                if file.endswith('.py') and 'main' in file.lower():
                    full_path = os.path.join(root, file)
                    print(f"Found alternative entry point: {full_path}")
                    return full_path
    
    # If still no entry point found, check if original src structure exists
    src_path = os.path.join(obfuscated_dir, "src")
    if os.path.exists(src_path):
        for candidate in entry_candidates:
            for root, dirs, files in os.walk(src_path):
                if candidate in files:
                    full_path = os.path.join(root, candidate)
                    print(f"Found entry point in src structure: {full_path}")
                    return full_path
    
    print("Could not find suitable entry point in obfuscated folder")
    return None

def create_partial_protected_spec():
    """Create a partial_protected spec file that works with partial obfuscation"""
    print("Creating partial_protected spec file for partial obfuscation...")
    
    # Find any Python file that could serve as entry point
    entry_point = None
    
    # Check original src directory
    for root, dirs, files in os.walk("src"):
        for file in ["main_page.py", "main.py", "app.py"]:
            if file in files:
                entry_point = os.path.join(root, file)
                break
        if entry_point:
            break
    
    if not entry_point:
        print("No suitable entry point found in original src")
        return False
    
    spec_content = f'''# -*- mode: python -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os
import sys

block_cipher = None
project_root = os.path.abspath('.')


a = Analysis(
    ['{entry_point.replace(os.sep, '/')}'],
    pathex=[project_root, 'src'],
    datas=[
        # Config files
        (os.path.join(project_root, 'src', 'config.yaml'), '.') if os.path.exists(os.path.join(project_root, 'src', 'config.yaml')) else None,
        
        # Data files
        (os.path.join(project_root, 'data', 'Steel_member_properties.xlsx'), 'data') if os.path.exists(os.path.join(project_root, 'data', 'Steel_member_properties.xlsx')) else None,
        (os.path.join(project_root, 'data', 'Input_Data.xlsx'), 'data') if os.path.exists(os.path.join(project_root, 'data', 'Input_Data.xlsx')) else None,
        
        # Source files (including any obfuscated ones)
        (os.path.join(project_root, 'src'), 'src'),
        
        # Include obfuscated files if they exist
        (os.path.join(project_root, 'pyarmor_obfuscated', 'src'), 'pyarmor_obfuscated_src') if os.path.exists(os.path.join(project_root, 'pyarmor_obfuscated', 'src')) else None,
        
        # PyArmor runtime files if they exist
        (os.path.join(project_root, 'pyarmor_obfuscated', 'pyarmor_runtime_000000'), 'pyarmor_runtime_000000') if os.path.exists(os.path.join(project_root, 'pyarmor_obfuscated', 'pyarmor_runtime_000000')) else None,
    ],
    hiddenimports=[
        'tkinter', 'tkinter.filedialog', 'mysql', 'mysql.connector',
        'flet', 'sqlite3', 'pandas', 'openpyxl', 'yaml', 'scipy', 'numpy',
        'asyncio', 'asyncio.windows_events', 'apscheduler', 'requests',
        'apscheduler.schedulers', 'apscheduler.schedulers.base',
        'apscheduler.triggers.date', 'plxscripting', 'plxscripting.easy',
        'xlsxwriter', 'openpyxl',
        'pyarmor_runtime_000000', 'pytransform',
        *collect_submodules('flet_core'),
        *collect_submodules('flet_async'),
        *collect_submodules('apscheduler')
    ],
    hookspath=[], hooksconfig={{}}, runtime_hooks=[], excludes=[],
    win_no_prefer_redirects=False, win_private_assemblies=False,
    cipher=block_cipher, noarchive=False,
)

# Filter out None values from datas
a.datas = [item for item in a.datas if item is not None]

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
    icon=None,
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
'''
    
    with open('build_partial_protected.spec', 'w') as f:
        f.write(spec_content)
    print("✓ Created build_partial_protected.spec")
    return True

def create_pyarmor_spec():
    """Create spec file for PyArmor obfuscated build"""
    
    # Find the correct entry point
    entry_point = find_main_entry_point()
    if not entry_point:
        print("Could not find entry point in obfuscated folder, creating partial_protected spec...")
        return create_partial_protected_spec()
    
    # Determine the correct source paths based on what actually exists
    obfuscated_paths = {}
    
    for root, dirs, files in os.walk("pyarmor_obfuscated"):
        # Look for important directories
        dir_name = os.path.basename(root)
        if dir_name in ['frontend', 'plaxis', 'src']:
            obfuscated_paths[dir_name] = root
    
    print(f"Obfuscated paths found: {obfuscated_paths}")
    
    spec_content = f'''# -*- mode: python -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os
import sys

block_cipher = None
project_root = os.path.abspath('.')

a = Analysis(
    ['{entry_point.replace(os.sep, '/')}'],
    pathex=[project_root, 'pyarmor_obfuscated'],
    datas=[
        # Config files
        (os.path.join(project_root, 'src', 'config.yaml'), '.') if os.path.exists(os.path.join(project_root, 'src', 'config.yaml')) else None,
        
        # Data files
        (os.path.join(project_root, 'data', 'Steel_member_properties.xlsx'), 'data') if os.path.exists(os.path.join(project_root, 'data', 'Steel_member_properties.xlsx')) else None,
        (os.path.join(project_root, 'data', 'Input_Data.xlsx'), 'data') if os.path.exists(os.path.join(project_root, 'data', 'Input_Data.xlsx')) else None,
        (os.path.join(project_root, 'data'), 'data') if os.path.exists(os.path.join(project_root, 'data')) else None,
        
        # PyArmor obfuscated source files'''
    
    # Add obfuscated paths dynamically
    for dir_name, path in obfuscated_paths.items():
        spec_content += f'''
        (os.path.join(project_root, '{path.replace(os.sep, '/')}'), '{dir_name}'),'''
    
    # Add PyArmor runtime files
    spec_content += '''
        
        # PyArmor runtime files
        (os.path.join(project_root, 'pyarmor_obfuscated', 'pyarmor_runtime_000000'), 'pyarmor_runtime_000000') if os.path.exists(os.path.join(project_root, 'pyarmor_obfuscated', 'pyarmor_runtime_000000')) else None,
    ],
    hiddenimports=[
        'tkinter', 'tkinter.filedialog', 'mysql', 'mysql.connector',
        'flet', 'sqlite3', 'pandas', 'openpyxl', 'yaml', 'scipy', 'numpy',
        'asyncio', 'asyncio.windows_events', 'apscheduler', 'requests',
        'apscheduler.schedulers', 'apscheduler.schedulers.base',
        'apscheduler.triggers.date', 'plxscripting', 'plxscripting.easy',
        'xlsxwriter', 'openpyxl',
        'pyarmor_runtime_000000', 'pytransform',
        *collect_submodules('flet_core'),
        *collect_submodules('flet_async'),
        *collect_submodules('apscheduler')
    ],
    hookspath=[], hooksconfig={{}}, runtime_hooks=[], excludes=[],
    win_no_prefer_redirects=False, win_private_assemblies=False,
    cipher=block_cipher, noarchive=False,
)

# Filter out None values from datas
a.datas = [item for item in a.datas if item is not None]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    icon=None,
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
'''
    
    spec_file = 'build_pyarmor.spec'
    with open(spec_file, 'w') as f:
        f.write(spec_content)
    print(f"✓ Created {spec_file}")
    return True

def build_executable():
    """Build the executable with PyArmor protection"""
    
    # Determine which spec file to use
    if os.path.exists('build_pyarmor.spec'):
        spec_file = 'build_pyarmor.spec'
        print("Building with PyArmor protected spec...")
    elif os.path.exists('build_partial_protected.spec'):
        spec_file = 'build_partial_protected.spec'
        print("Building with partial_protected spec...")
    else:
        print("No spec file found!")
        return False
    
    result = run_command(f"pyinstaller {spec_file}")
    
    # Check if dist directory was created
    dist_dir = os.path.join(os.getcwd(), "dist")
    if not os.path.exists(dist_dir):
        print("\n✗ PyInstaller build failed - dist directory not created")
        return False
    
    # Check if the expected output directory exists
    app_name = "GeoCoPilot"
    app_dir = os.path.join(dist_dir, app_name)
    if not os.path.exists(app_dir):
        print(f"\n✗ Expected output directory not found: {app_dir}")
        print("Contents of dist directory:")
        for item in os.listdir(dist_dir):
            item_path = os.path.join(dist_dir, item)
            if os.path.isdir(item_path):
                print(f"  - [DIR] {item}")
            else:
                print(f"  - [FILE] {item}")
        
        # Check if there's an alternative directory
        for item in os.listdir(dist_dir):
            item_path = os.path.join(dist_dir, item)
            if os.path.isdir(item_path) and app_name.lower() in item.lower():
                print(f"\n⚠️  Found alternative directory: {item}")
                print("This might be the build output. Check if it contains GeoCoPilot.exe")
                return True
        
        return False
    
    return True

def check_inno_setup():
    """Check if Inno Setup is installed"""
    try:
        # Check common installation paths
        paths = [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe"
        ]
        for path in paths:
            if os.path.exists(path):
                print(f"✓ Found Inno Setup at: {path}")
                return path
        
        # Check if it's in PATH
        result = subprocess.run("ISCC", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            print("✓ Found Inno Setup in PATH")
            return "ISCC"
            
    except Exception:
        pass
    
    print("✗ Inno Setup not found")
    return None

def create_installer():
    """Create an installer using Inno Setup"""
    print("\nCreating installer with Inno Setup...")
    
    # Check if Inno Setup is available
    inno_path = check_inno_setup()
    if not inno_path:
        print("Inno Setup not installed. Please install it to create the installer.")
        print("Download from: https://jrsoftware.org/isdl.php")
        return False
    
    # Prepare paths
    project_root = os.path.abspath('.')
    app_name = "GeoCoPilot"
    
    # Find the actual output directory
    dist_dir = os.path.join(project_root, "dist")
    app_dir = None
    
    # Look for directory containing the executable
    for item in os.listdir(dist_dir):
        item_path = os.path.join(dist_dir, item)
        if os.path.isdir(item_path):
            # Check if it contains the expected executable
            exe_path = os.path.join(item_path, f"{app_name}.exe")
            if os.path.exists(exe_path):
                app_dir = item_path
                break
            # Check for alternative naming
            for file in os.listdir(item_path):
                if file.endswith('.exe') and app_name.lower() in file.lower():
                    app_dir = item_path
                    print(f"Found alternative executable: {file}")
                    break
            if app_dir:
                break
    
    if not app_dir or not os.path.exists(app_dir):
        print(f"✗ Could not find application directory in: {dist_dir}")
        print("Contents of dist directory:")
        for item in os.listdir(dist_dir):
            item_path = os.path.join(dist_dir, item)
            if os.path.isdir(item_path):
                print(f"  - [DIR] {item}")
                exe_found = False
                for file in os.listdir(item_path):
                    if file.endswith('.exe'):
                        print(f"    - EXE: {file}")
                        exe_found = True
                if not exe_found:
                    print("    - No EXE files found in this directory")
            else:
                print(f"  - [FILE] {item}")
        return False
    
    print(f"✓ Found application directory: {app_dir}")
    
    installer_dir = os.path.join(project_root, "installer")
    output_setup = os.path.join(installer_dir, f"{app_name}_Setup.exe")
    
    # Create installer directory
    os.makedirs(installer_dir, exist_ok=True)
    
    # Create ISS script content
    iss_content = f"""; Inno Setup Script for {app_name}
[Setup]
AppName={app_name}
AppVersion=1.0
DefaultDirName={{autopf}}\\{app_name}
DefaultGroupName={app_name}
OutputDir={installer_dir.replace('\\', '\\\\')}
OutputBaseFilename={app_name}_Setup
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "{app_dir}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{{group}}\\{app_name}"; Filename: "{{app}}\\{app_name}.exe"
Name: "{{commondesktop}}\\{app_name}"; Filename: "{{app}}\\{app_name}.exe"

[Run]
Filename: "{{app}}\\{app_name}.exe"; Description: "Run {app_name}"; Flags: nowait postinstall skipifsilent
"""
    
    # Write ISS file
    iss_path = os.path.join(project_root, "installer_script.iss")
    with open(iss_path, "w") as f:
        f.write(iss_content)
    print(f"✓ Created Inno Setup script: {iss_path}")
    
    # Run Inno Setup compiler
    cmd = f'"{inno_path}" "{iss_path}"'
    result = run_command(cmd)
    
    if result and os.path.exists(output_setup):
        print(f"\n✓ Installer created successfully: {output_setup}")
        print("This installer will guide users through the installation process")
        return True
    
    print("✗ Installer creation failed")
    return False

def main():
    """Main build process with PyArmor protection"""
    print("=== Improved PyArmor + PyInstaller Protected Build ===")
    
    # Check PyArmor installation
    if not check_pyarmor_installation():
        sys.exit(1)
    
    # Clean previous builds
    clean_previous_builds()
    
    # Obfuscate with PyArmor
    if not obfuscate_with_pyarmor():
        print("PyArmor obfuscation failed completely")
        # Continue with partial_protected approach
        if not create_partial_protected_spec():
            sys.exit(1)
    else:
        # Create spec file based on obfuscation results
        if not create_pyarmor_spec():
            sys.exit(1)
    
    # Build executable
    if build_executable():
        print("\n=== Build completed ===")
        
        # Create installer
        if create_installer():
            print("\n=== Installer created ===")
        else:
            print("\n=== ✗Installer creation failed===")
    else:
        print("\n=== Build Failed ===")

if __name__ == "__main__":
    main()