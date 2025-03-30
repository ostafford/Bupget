"""
Security CLI commands.

This module provides commands for security-related operations.
"""

import click
from flask.cli import with_appcontext

@click.command('generate-encryption-key')
@with_appcontext
def generate_encryption_key_command():
    """Generate a new encryption key and store it to a file."""
    from app.utils.crypto import generate_encryption_key, store_encryption_key_to_file
    
    # Generate a new key
    key = generate_encryption_key()
    
    # Store it to file
    store_encryption_key_to_file(key)
    
    click.echo("✅ Generated new encryption key and stored it to .encryption_key file")
    click.echo("⚠️  Keep this file secure and add it to your .gitignore!")
    
    # Also display the key so it can be added to environment variables if desired
    click.echo("\nKey (for ENCRYPTION_KEY environment variable):")
    click.echo(key.decode('utf-8'))

def register_security_commands(app):
    """Register security CLI commands with the Flask application."""
    app.cli.add_command(generate_encryption_key_command)
