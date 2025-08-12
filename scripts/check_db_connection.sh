#!/bin/bash
#
# check_db_connection.sh
#
# This script checks the connection to the default database as configured in Django's settings.py.
# To test the PRODUCTION (Aurora DSQL) connection, your .env file MUST contain:
#
# DEBUG=False
# AWS_ACCESS_KEY_ID=<your_key_id>
# AWS_SECRET_ACCESS_KEY=<your_secret_key>
# AURORA_DSQL_HOST=<your_aurora_host>
# AURORA_DSQL_DATABASE=atilanogarciawebsitedb
# AURORA_DSQL_USER=<your_db_user>
# AWS_REGION=<your_aws_region>
#
# Make sure you have run ./setup.sh or manually created the venv and installed requirements.

# Exit immediately if a command exits with a non-zero status.
set -e

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Checking database connection..."
# The Django 'check' command will attempt to connect to the database.
# It will use the logic in settings.py to determine which database to use based on the DEBUG flag.
python manage.py check --database default

echo "✅ Database connection check completed successfully."
echo "If there were no errors above, the connection is configured correctly."
