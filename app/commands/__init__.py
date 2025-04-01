"""
Commands package initialization.

This file makes the directory a Python package and provides the function
for registering all commands with the Flask CLI.
"""

def register_commands(app):
    """Register all CLI commands with the Flask application."""
    # Import and register basic commands
    from app.commands.core import register_core_commands
    register_core_commands(app)
    
    # Import and register user management commands
    from app.commands.user import register_user_commands
    register_user_commands(app)
    
    # Import and register account commands
    from app.commands.account import register_account_commands
    register_account_commands(app)
    
    # Import and register transaction commands
    from app.commands.transaction import register_transaction_commands
    register_transaction_commands(app)
    
    # Import and register Up Bank commands
    from app.commands.upbank import register_upbank_commands
    register_upbank_commands(app)
    
    # Import and register webhook commands
    from app.commands.webhook import register_webhook_commands
    register_webhook_commands(app)

    # Import and register Up Bank test commands
    from app.commands.upbank_test import register_upbank_test_commands
    register_upbank_test_commands(app)

