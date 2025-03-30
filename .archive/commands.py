"""
Command registration.

This module handles registration of CLI commands with the Flask application.
"""

def register_commands(app_instance):
    """Register CLI commands with the Flask application."""
    global app
    app = app_instance  # Store app reference for verify-setup command
    
    # Import and register the commands from other modules
    from Bupget.commands import (
        init_db_command, drop_db_command, create_demo_user_command,
        verify_setup_command, reset_db_command, delete_user_command,
        list_users_command
    )
    
    # Basic application commands
    app.cli.add_command(init_db_command)
    app.cli.add_command(drop_db_command)
    app.cli.add_command(create_demo_user_command)
    app.cli.add_command(verify_setup_command)
    app.cli.add_command(reset_db_command)
    
    # User management commands
    app.cli.add_command(delete_user_command)
    app.cli.add_command(list_users_command)
    
    # Try to import and register Up Bank commands
    try:
        from app.commands.upbank_commands import (
            connect_up_bank_command, sync_up_bank_command, 
            test_upbank_auth_command, sync_accounts_command,
            list_accounts_command, test_get_accounts_command
        )
        
        app.cli.add_command(connect_up_bank_command)
        app.cli.add_command(sync_up_bank_command)
        app.cli.add_command(test_upbank_auth_command)
        app.cli.add_command(sync_accounts_command)
        app.cli.add_command(list_accounts_command)
        app.cli.add_command(test_get_accounts_command)
    except ImportError as e:
        print(f"Warning: Could not import Up Bank commands: {e}")
    
    # Try to import and register security commands
    try:
        from app.commands.security_commands import generate_encryption_key_command
        app.cli.add_command(generate_encryption_key_command)
    except ImportError as e:
        print(f"Warning: Could not import security commands: {e}")
    
    # Try to register transaction commands
    try:
        from app.commands.transaction_commands import register_transaction_commands
        register_transaction_commands(app)
    except ImportError:
        print("Warning: Could not import transaction commands")
    
    # Try to register webhook commands
    try:
        from app.commands.webhook_commands import register_webhook_commands
        register_webhook_commands(app)
    except ImportError:
        print("Warning: Could not import webhook commands")
