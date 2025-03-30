"""
Account management commands.

This module provides commands for managing financial accounts.
"""

import click
from flask.cli import with_appcontext

@click.command('list-accounts')
@click.argument('user_id', type=int)
@with_appcontext
def list_accounts_command(user_id):
    """
    List accounts for a user.
    
    Args:
        user_id: The user ID
    """
    from app.models import User, Account
    
    # Find the user
    user = User.query.get(user_id)
    
    if not user:
        click.echo(f'User with ID {user_id} not found.')
        return
    
    # Get accounts
    accounts = Account.query.filter_by(user_id=user_id).all()
    
    if not accounts:
        click.echo(f'No accounts found for user {user_id}.')
        return
    
    click.echo(f'Accounts for user {user.full_name} (ID: {user_id}):')
    for account in accounts:
        click.echo(f'  ID: {account.id}')
        click.echo(f'  Name: {account.name}')
        click.echo(f'  Type: {account.type.value}')
        click.echo(f'  Balance: {account.balance} {account.currency}')
        click.echo(f'  Source: {account.source.value}')
        click.echo(f'  Last Synced: {account.last_synced}')
        click.echo(f'  External ID: {account.external_id}')
        click.echo('  ------------------')

@click.command('sync-accounts')
@click.argument('user_id', type=int)
@with_appcontext
def sync_accounts_command(user_id):
    """
    Sync accounts from Up Bank for a user.
    
    Args:
        user_id: The user ID
    """
    from app.services.bank_service import sync_accounts
    
    success, message, count = sync_accounts(user_id)
    
    if success:
        click.echo(f"✅ {message}")
    else:
        click.echo(f"❌ {message}")

def register_account_commands(app):
    """Register account management CLI commands with the Flask application."""
    app.cli.add_command(list_accounts_command)
    app.cli.add_command(sync_accounts_command)