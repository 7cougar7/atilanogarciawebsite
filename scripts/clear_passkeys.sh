#!/bin/bash

# This script clears all passkeys from the database by running the
# custom Django management command `clear_passkeys`.

# Ensure the script is run from the project root
cd "$(dirname "$0")"

echo "Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found at venv/bin/activate"
    exit 1
fi

echo "Running the clear_passkeys management command..."
python manage.py clear_passkeys

# The virtual environment is not explicitly deactivated,
# as the script will exit and the shell session will return to normal.

echo "Passkey clearing process complete."
