from setuptools import setup
from Cython.Build import cythonize
import glob
import os

# Find all Python files but exclude problematic ones
py_files = []
exclude_files = [
    'src/plaxis/Materials.py',  # Has undefined variables
    'src/frontend/main_page.py'  # Keep as regular Python for easier debugging
]

for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".py"):
            full_path = os.path.join(root, file)
            # Normalize path for comparison
            normalized_path = full_path.replace('\\', '/')
            if normalized_path not in exclude_files:
                py_files.append(full_path)

print(f"Files to compile: {len(py_files)}")
for file in py_files:
    print(f"  - {file}")

print(f"Excluded files: {len(exclude_files)}")
for file in exclude_files:
    print(f"  - {file}")

setup(
    ext_modules=cythonize(py_files, compiler_directives={'language_level': 3})
)