#!/usr/bin/env python3
"""
FontAwesome Setup Script

This script extracts the full FontAwesome zip file to the correct static directory
before Django's collectstatic command runs. This ensures all FontAwesome icons
are available in the application.

Usage:
    python setup_fontawesome.py

This should be run before:
    python manage.py collectstatic
"""

import shutil
import zipfile
from pathlib import Path


def setup_fontawesome():
    """Extract FontAwesome zip to static directory."""

    # Define paths
    project_root = Path(
        __file__
    ).parent.parent  # Go up one level from scripts/ to project root
    static_dir = project_root / "mainwebsite" / "static"
    fontawesome_zip = static_dir / "fontawesome-free-6.7.2.zip"
    fontawesome_static_dir = static_dir / "fontawesome"

    print("Setting up FontAwesome static files...")

    # Check if zip file exists
    if not fontawesome_zip.exists():
        print(f"ERROR: FontAwesome zip file not found at {fontawesome_zip}")
        return False

    # Create static directory if it doesn't exist
    static_dir.mkdir(parents=True, exist_ok=True)

    # Remove existing fontawesome directory to ensure clean extraction
    if fontawesome_static_dir.exists():
        print(f"Removing existing FontAwesome directory: {fontawesome_static_dir}")
        shutil.rmtree(fontawesome_static_dir)

    # Extract the zip file
    print(f"Extracting {fontawesome_zip}...")
    with zipfile.ZipFile(fontawesome_zip, "r") as zip_ref:
        # Extract to temporary location first
        temp_extract_dir = project_root / "temp_fontawesome_extract"
        zip_ref.extractall(temp_extract_dir)

        # Find the extracted fontawesome directory (it should be fontawesome-free-6.7.2-web)
        extracted_dirs = [d for d in temp_extract_dir.iterdir() if d.is_dir()]
        if not extracted_dirs:
            print("ERROR: No directories found in extracted zip")
            shutil.rmtree(temp_extract_dir)
            return False

        fontawesome_extracted = extracted_dirs[0]

        # Move the contents to the correct static location
        print(f"Moving FontAwesome files to {fontawesome_static_dir}...")
        shutil.move(str(fontawesome_extracted), str(fontawesome_static_dir))

        # Clean up temp directory
        shutil.rmtree(temp_extract_dir)

    # Verify the extraction was successful
    css_dir = fontawesome_static_dir / "css"
    webfonts_dir = fontawesome_static_dir / "webfonts"
    js_dir = fontawesome_static_dir / "js"

    if css_dir.exists() and webfonts_dir.exists():
        print("✅ FontAwesome extraction successful!")
        print(f"   CSS files: {len(list(css_dir.glob('*.css')))} files")
        print(f"   Web fonts: {len(list(webfonts_dir.glob('*')))} files")
        if js_dir.exists():
            print(f"   JS files: {len(list(js_dir.glob('*.js')))} files")
        return True
    else:
        print("ERROR: FontAwesome extraction appears to have failed")
        return False


if __name__ == "__main__":
    success = setup_fontawesome()
    if not success:
        exit(1)
    print("\nFontAwesome is ready! You can now run 'python manage.py collectstatic'")
