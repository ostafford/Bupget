"""
Core application commands.

This module provides essential commands for database management and application setup.
"""

import click
from flask.cli import with_appcontext
from app.extensions import db

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database - create all tables."""
    db.create_all()
    click.echo('Initialized the database.')

@click.command('drop-db')
@with_appcontext
def drop_db_command():
    """Drop all database tables - DANGEROUS!"""
    if click.confirm('Are you sure you want to drop all tables? This cannot be undone!'):
        db.drop_all()
        click.echo('Dropped all tables.')
    else:
        click.echo('Operation canceled.')

@click.command('verify-setup')
@with_appcontext
def verify_setup_command():
    """Verify that the application setup is working correctly."""
    # Check database connection
    try:
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        click.echo('✅ Database connection successful')
    except Exception as e:
        click.echo(f'❌ Database connection failed: {str(e)}')
    
    # Check environment variables
    import os
    required_vars = ['FLASK_CONFIG', 'SECRET_KEY', 'DATABASE_URI']
    for var in required_vars:
        if os.environ.get(var):
            click.echo(f'✅ Environment variable {var} is set')
        else:
            click.echo(f'❌ Environment variable {var} is missing or empty')
    
    # Check if models are accessible
    try:
        from app.models import User
        click.echo('✅ Models can be imported')
    except Exception as e:
        click.echo(f'❌ Model import failed: {str(e)}')
    
    click.echo('\nSetup verification complete.')

@click.command('reset-db')
@click.option('--yes', is_flag=True, help='Skip confirmation prompt')
@with_appcontext
def reset_db_command(yes):
    """Reset the database - drop all tables and recreate them."""
    if not yes:
        confirmed = click.confirm('Are you sure you want to reset the database? This will delete ALL data!')
        if not confirmed:
            click.echo('Operation cancelled.')
            return
    
    # Drop all tables
    db.drop_all()
    click.echo('Dropped all tables.')
    
    # Recreate all tables
    db.create_all()
    click.echo('Recreated all tables.')
    
    # Create demo user if desired
    if click.confirm('Create demo user?'):
        from app.models.user import User
        
        user = User(
            email='demo@example.com',
            first_name='Demo',
            last_name='User'
        )
        user.password = 'password'  # This will be hashed
        
        db.session.add(user)
        db.session.commit()
        
        click.echo('Created demo user with:')
        click.echo('  Email: demo@example.com')
        click.echo('  Password: password')

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

def register_core_commands(app):
    """Register core CLI commands with the Flask application."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(drop_db_command)
    app.cli.add_command(verify_setup_command)
    app.cli.add_command(reset_db_command)
    app.cli.add_command(generate_encryption_key_command)
    