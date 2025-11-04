# GeoCoPilot Installation Guide

## Prerequisites
- Python 3.9 or higher
- pip package manager
- SQLite (included with Python)
- Git (for cloning the repository)
- Recommended: Virtual environment (venv)

## Getting Started

### Cloning the Repository
To get a local copy of the project, run:
```bash
git clone https://github.com/yourusername/geo-co-pilot.git
cd geo-co-pilot
```

### Installation

Set up a virtual environment (recommended):
```bash
# Create virtual environment
python -m venv venv

# On macOS/Linux
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

Install required dependencies:
```bash
pip install -r requirements.txt
```

### Configuration

- The application uses `config.yaml` for database and application settings
- By default, it creates and uses a SQLite database at `data/flet.db`
- To modify database settings or other configurations, edit `src/config.yaml`

### Running the Application

#### Development Mode
For development and testing:
```bash
python src/frontend/main_page.py
```

#### Quick Start Option
You can build and run the protected application using these methods:
##### Prerequisites:
- Install Inno Setup from: https://jrsoftware.org/isdl.php

- Download "Inno Setup 6" (latest stable version)
- Install with default settings


#### Option 1: Build Protected Executable (Recommended)
```bash
# Install build dependencies
pip install -r requirements_build_installer.txt

# Clean previous builds
Remove-Item -Recurse -Force .\build, .\dist, .\protected_src, .\pyarmor_obfuscated, .\installer -ErrorAction SilentlyContinue


# Build protected executable
python advanced_protection_build.py
```
#### Option 2: Cython Obfuscated Build (Maximum Protection)
##### Prerequisites:

- Install Cython: pip install cython

```bash
# Clean previous builds
Remove-Item -Recurse -Force .\build, .\dist, .\*.spec -ErrorAction SilentlyContinue


# Compile Python files to C extensions using Cython
python setup.py build_ext --inplace


# Create executable with PyInstaller
pyinstaller --onefile --noconsole --add-data "src;src" --add-data "data;data" --paths "src" --name "GeoCoPilot" src/frontend/main_page.py
```
#### Option 3: Standard Build (No Protection)
```bash
# Clean previous builds
Remove-Item -Recurse -Force .\build, .\dist -ErrorAction SilentlyContinue

# Rebuild with standard config
pyinstaller build.spec
```
##### If directly run the EXE
- Navigate to `geo_co_pilot\dist` folder
- Run `GeoCoPilot.exe` to launch the application'

##### If run the Installer
- Navigate to geo_co_pilot\installer folder
- Right-click on GeoCoPilot_Setup.exe and select "Run as administrator"

- Installation location (default: C:\Program Files\GeoCoPilot)


### Post-Installation Notes
- The first run will create necessary data files in the data directory

- All generated files (databases, Excel reports) will be stored in data/


### Troubleshooting 
#### Common Issues:

- DLL Errors: Install Microsoft Visual C++ Redistributable

- Missing Files: Verify file paths in config.yaml

- Database Issues: Delete data/flet.db to reset