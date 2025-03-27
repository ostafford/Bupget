"""
CLI commands for the application.

This module defines CLI commands that can be run with 'flask [command]'.
"""

import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models import User, Account, Transaction, RecurringExpense


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
    
    click.echo('Created demo user with email: demo@example.com and password: password')


def register_commands(app):
    """Register CLI commands with the Flask application."""
    app.cli.add_command(init_db_command)
    app.cli.add_command(drop_db_command)
    app.cli.add_command(create_demo_user_command)
    