"""
User management CLI commands.

This module provides commands for managing users in the application.
"""

import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models import User

@click.command('create-demo-user')
@with_appcontext
def create_demo_user_command():
    """Create a demo user for testing."""
    # Check if demo user already exists
    if User.query.filter_by(email='demo@example.com').first():
        click.echo('Demo user already exists.')
        return
    
    # Create demo user
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
    click.echo('\nYou can now log in with these credentials to test the application.')


@click.command('delete-user')
@click.argument('email')
@with_appcontext
def delete_user_command(email):
    """Delete a user by email."""
    # Find the user
    user = User.query.filter_by(email=email).first()
    
    if not user:
        click.echo(f'User with email {email} not found.')
        return
    
    # Delete the user
    db.session.delete(user)
    db.session.commit()
    
    click.echo(f'Deleted user with email: {email}')


@click.command('list-users')
@with_appcontext
def list_users_command():
    """List all users in the database."""
    users = User.query.all()
    
    if not users:
        click.echo('No users found in the database.')
        return
    
    click.echo('Users in the database:')
    for user in users:
        click.echo(f'  ID: {user.id}, Email: {user.email}, Name: {user.full_name}')


def register_user_commands(app):
    """Register user management CLI commands with the Flask application."""
    app.cli.add_command(create_demo_user_command)
    app.cli.add_command(delete_user_command)
    app.cli.add_command(list_users_command)
