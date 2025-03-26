#!/bin/bash

# This script fixes the Python environment for the Budget App

echo "=== Budget App Environment Fix ==="

# Uninstall problematic packages
echo "Removing any conflicting packages..."
pip uninstall -y flask werkzeug

# Install PostgreSQL dependencies if needed
echo "Installing PostgreSQL dependencies..."
apt-get update
apt-get install -y libpq-dev

# Install fixed requirements
echo "Installing dependencies with fixed versions..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit the .env file to add your configuration."
fi

echo "=== Environment Fixed ==="
echo "You should now be able to run the application."
echo "Try running: export FLASK_APP=run.py && flask run"