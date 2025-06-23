# create_init.py
# create __init__.py files in all relevant subdirectories of the project
# this ensures Python treats these directories as packages
# useful for enabling relative and absolute imports throughout the codebase
# run this script once after cloning or reorganizing project structure

import os

# List of directories that should be treated as Python packages
directories = [
    "config",
    "core",
    "gui",
    "csi_io",
    "processing"
]

# Base path: assumed to be the root of the project (same directory as this script)
base_path = os.path.dirname(os.path.abspath(__file__))

# Create __init__.py in each directory if it doesn't already exist
for folder in directories:
    full_path = os.path.join(base_path, folder)
    init_file = os.path.join(full_path, "__init__.py")
    
    if not os.path.exists(init_file):
        os.makedirs(full_path, exist_ok=True)  # ensure the directory exists
        with open(init_file, "w", encoding="utf-8") as f:
            f.write("# Package initializer\n")
        print(f"✅ Created: {init_file}")
    else:
        print(f"✔️ Already exists: {init_file}")
