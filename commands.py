"""
CLI commands for the application.

This module defines CLI commands that can be run with 'flask [command]'.
This file is kept for backward compatibility. The actual commands are now
organized in the app/commands/ package.
"""

# Import the register_commands function from the commands package
from app.commands import register_commands