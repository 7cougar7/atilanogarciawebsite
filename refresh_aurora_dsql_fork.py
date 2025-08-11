#!/usr/bin/env python3
"""
Aurora DSQL Django Fork Refresh Script (Python version)

This script fetches the latest commit from your fork and reinstalls it.
Usage: python refresh_aurora_dsql_fork.py
"""

import os
import re
import subprocess
import sys
from pathlib import Path

# Configuration
REPO_URL = "https://github.com/7cougar7/aurora-dsql-django.git"
BRANCH = "version-0"
PACKAGE_NAME = "aurora-dsql-django"


# Colors for output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


def print_colored(message, color=Colors.NC):
    """Print a colored message."""
    print(f"{color}{message}{Colors.NC}")


def run_command(command, check=True, capture_output=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command, shell=True, check=check, capture_output=capture_output, text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print_colored("❌ Command failed: " + command, Colors.RED)
        print_colored("Error: " + str(e), Colors.RED)
        if capture_output and e.stdout:
            print_colored("Stdout: " + e.stdout, Colors.RED)
        if capture_output and e.stderr:
            print_colored("Stderr: " + e.stderr, Colors.RED)
        sys.exit(1)


def get_latest_commit():
    """Get the latest commit hash from the remote repository."""
    print_colored(
        "🔍 Fetching latest commit hash from " + REPO_URL + "...", Colors.BLUE
    )

    result = run_command(f"git ls-remote {REPO_URL} {BRANCH}")
    if result.stdout:
        commit_hash = result.stdout.split()[0]
        print_colored("✅ Latest commit: " + commit_hash, Colors.GREEN)
        return commit_hash
    else:
        print_colored("❌ Failed to fetch latest commit hash", Colors.RED)
        sys.exit(1)


def check_current_installation():
    """Check if the package is currently installed."""
    print_colored("🔍 Checking current installation...", Colors.BLUE)

    result = run_command(f"pip show {PACKAGE_NAME}", check=False)
    if result.returncode == 0:
        print_colored("📦 Current installation found:", Colors.YELLOW)
        # Extract relevant info
        for line in result.stdout.split("\n"):
            if any(field in line for field in ["Name:", "Version:", "Location:"]):
                print(line)
        return True
    else:
        print_colored("📦 Package not currently installed", Colors.YELLOW)
        return False


def uninstall_package():
    """Uninstall the current package."""
    print_colored("🗑️  Uninstalling current version...", Colors.YELLOW)
    run_command(f"pip uninstall {PACKAGE_NAME} -y")


def install_latest_version(commit_hash):
    """Install the latest version from the fork."""
    print_colored("📥 Installing latest version from fork...", Colors.BLUE)

    install_url = "git+" + REPO_URL + "@" + commit_hash
    print_colored("Installing: " + install_url, Colors.BLUE)

    run_command('pip install --force-reinstall --no-cache-dir "' + install_url + '"')
    print_colored("✅ Successfully installed latest version!", Colors.GREEN)


def show_installation_info():
    """Show information about the installed package."""
    print_colored("📋 Installation details:", Colors.BLUE)
    result = run_command(f"pip show {PACKAGE_NAME}")
    for line in result.stdout.split("\n"):
        if any(field in line for field in ["Name:", "Version:", "Location:"]):
            print(line)


def update_requirements_in(commit_hash):
    """Update requirements.in with the new commit hash."""
    requirements_file = Path("requirements.in")

    if not requirements_file.exists():
        print_colored("⚠️  requirements.in not found, skipping update", Colors.YELLOW)
        return

    print_colored("📝 Updating requirements.in with latest commit...", Colors.BLUE)

    # Create backup
    backup_file = Path("requirements.in.backup")
    requirements_file.rename(backup_file)

    # Read and update content
    with open(backup_file, "r") as f:
        content = f.read()

    # Update the git URL with new commit hash
    pattern = r"git\+https://github\.com/7cougar7/aurora-dsql-django\.git@[a-f0-9]+"
    replacement = (
        "git+https://github.com/7cougar7/aurora-dsql-django.git@" + commit_hash
    )
    updated_content = re.sub(pattern, replacement, content)

    # Write updated content
    with open(requirements_file, "w") as f:
        f.write(updated_content)

    print_colored(
        "✅ Updated requirements.in with commit: " + commit_hash, Colors.GREEN
    )

    # Ask if user wants to recompile requirements.txt
    response = input(
        Colors.YELLOW
        + "🤔 Do you want to recompile requirements.txt? (y/n): "
        + Colors.NC
    )
    if response.lower().startswith("y"):
        print_colored("🔄 Recompiling requirements.txt...", Colors.BLUE)
        run_command("pip-compile")
        print_colored("✅ Requirements.txt updated", Colors.GREEN)


def test_installation():
    """Test that the installation works correctly."""
    print_colored("🧪 Testing installation...", Colors.BLUE)

    test_script = """
import aurora_dsql_django
from aurora_dsql_django.base import DatabaseWrapper
from aurora_dsql_django.schema import DatabaseSchemaEditor
print('✅ All imports successful')
print(f'Package location: {aurora_dsql_django.__file__}')
print(f'Version: {getattr(aurora_dsql_django, "__version__", "Unknown")}')
    """

    result = run_command('python -c "' + test_script + '"', check=False)
    if result.returncode == 0:
        print_colored("✅ Installation test passed!", Colors.GREEN)
        return True
    else:
        print_colored("❌ Installation test failed", Colors.RED)
        return False


def main():
    """Main function."""
    print_colored("🔄 Aurora DSQL Django Fork Refresh Script", Colors.BLUE)
    print("=" * 50)

    # Check if we're in a virtual environment
    if not os.environ.get("VIRTUAL_ENV"):
        print_colored("⚠️  Virtual environment not detected!", Colors.YELLOW)
        print_colored("Please activate your virtual environment first:", Colors.YELLOW)
        print_colored("source venv/bin/activate", Colors.BLUE)
        sys.exit(1)

    print_colored(
        "✅ Virtual environment active: " + os.environ["VIRTUAL_ENV"], Colors.GREEN
    )

    try:
        # Get latest commit
        latest_commit = get_latest_commit()

        # Check current installation
        is_installed = check_current_installation()

        # Uninstall if needed
        if is_installed:
            uninstall_package()

        # Install latest version
        install_latest_version(latest_commit)

        # Show installation info
        show_installation_info()

        # Update requirements.in
        update_requirements_in(latest_commit)

        # Test installation
        if test_installation():
            print()
            print_colored("🎉 Fork refresh completed successfully!", Colors.GREEN)
            print_colored("Latest commit: " + latest_commit, Colors.BLUE)
            print_colored(
                "Package is ready to use with your latest changes.", Colors.BLUE
            )
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        print_colored("\n❌ Operation cancelled by user", Colors.YELLOW)
        sys.exit(1)
    except Exception as e:
        print_colored("❌ Unexpected error: " + str(e), Colors.RED)
        sys.exit(1)


if __name__ == "__main__":
    main()
