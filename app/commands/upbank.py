"""
Up Bank integration commands.

This module provides commands for managing Up Bank API integration.
"""

import click
from flask.cli import with_appcontext

@click.command('connect-up-bank')
@click.argument('user_id', type=int)
@click.argument('token', required=True)
@with_appcontext
def connect_up_bank_command(user_id, token):
    """
    Connect a user to Up Bank using the provided token.
    
    Args:
        user_id: The user ID
        token: The Up Bank personal access token
    """
    from app.services.auth_service import store_up_bank_token
    
    result = store_up_bank_token(user_id, token)
    
    if result:
        click.echo(f"Successfully connected user {user_id} to Up Bank")
    else:
        click.echo(f"Failed to connect user {user_id} to Up Bank")

@click.command('sync-up-bank')
@click.argument('user_id', type=int)
@click.option('--days', default=30, help='Number of days of history to sync')
@with_appcontext
def sync_up_bank_command(user_id, days):
    """
    Sync Up Bank transactions for a user.
    
    Args:
        user_id: The user ID
        days: Number of days of history to sync
    """
    from app.services.bank_service import sync_accounts, sync_transactions
    from app.models import User
    
    # Get the user
    user = User.query.get(user_id)
    if not user:
        click.echo(f"User with ID {user_id} not found.")
        return
    
    # Sync accounts
    success, message, accounts_count = sync_accounts(user_id)
    click.echo(f"Accounts: {message}")
    
    if success:
        # Sync transactions
        success, message, tx_count = sync_transactions(user_id, days_back=days)
        click.echo(f"Transactions: {message}")
    else:
        click.echo("Skipping transaction sync because account sync failed.")

@click.command('test-upbank-auth')
@click.argument('token', required=True)
@with_appcontext
def test_upbank_auth_command(token):
    """
    Test authentication with the Up Bank API.
    
    Args:
        token: The Up Bank personal access token
    """
    from app.api.up_bank import test_api_connection
    
    result = test_api_connection(token)
    
    if result:
        click.echo("✅ Successfully authenticated with Up Bank API")
    else:
        click.echo("❌ Failed to authenticate with Up Bank API")

@click.command('test-get-accounts')
@click.argument('user_id', type=int)
@with_appcontext
def test_get_accounts_command(user_id):
    """
    Test retrieving accounts from Up Bank for a user.
    
    Args:
        user_id: The user ID
    """
    from app.models import User
    from app.api.up_bank import get_up_bank_api
    
    # Get the user
    user = User.query.get(user_id)
    if not user:
        click.echo(f"User with ID {user_id} not found.")
        return
    
    # Get the token
    token = user.get_up_bank_token()
    if not token:
        click.echo("Up Bank token not found for user.")
        return
    
    # Initialize the API
    api = get_up_bank_api(token=token)
    
    # Get accounts
    click.echo("Retrieving accounts from Up Bank...")
    accounts = api.get_accounts()
    
    if not accounts:
        click.echo("No accounts found.")
        return
    
    # Display accounts
    click.echo(f"Found {len(accounts)} accounts:")
    for i, account in enumerate(accounts):
        account_id = account.get('id', 'Unknown')
        attributes = account.get('attributes', {})
        name = attributes.get('displayName', 'Unknown')
        account_type = attributes.get('accountType', 'Unknown')
        
        balance_data = attributes.get('balance', {})
        balance_value = balance_data.get('value', '0')
        currency = balance_data.get('currencyCode', 'AUD')
        
        click.echo(f"\nAccount {i+1}:")
        click.echo(f"  ID: {account_id}")
        click.echo(f"  Name: {name}")
        click.echo(f"  Type: {account_type}")
        click.echo(f"  Balance: {balance_value} {currency}")
    
    # Also test getting a specific account
    if accounts:
        first_account_id = accounts[0].get('id')
        click.echo(f"\nRetrieving details for account {first_account_id}...")
        account_details = api.get_account_by_id(first_account_id)
        
        if account_details:
            attributes = account_details.get('attributes', {})
            name = attributes.get('displayName', 'Unknown')
            click.echo(f"  Name: {name}")
            
            # Get balance
            balance = api.get_account_balance(first_account_id)
            if balance:
                click.echo(f"  Balance: {balance.get('value')} {balance.get('currencyCode')}")
        else:
            click.echo("Failed to retrieve account details.")

@click.command('test-sync-transactions')
@click.argument('user_id', type=int)
@click.option('--days', default=30, help='Number of days of history to sync')
@click.option('--verbose', is_flag=True, help='Show detailed transaction information')
@with_appcontext
def test_sync_transactions_command(user_id, days, verbose):
    """
    Test syncing transactions from Up Bank for a user.
    
    Args:
        user_id: The user ID
        days: Number of days of history to sync
        verbose: Whether to show detailed transaction information
    """
    from app.models import User, Transaction
    
    # Get the user
    user = User.query.get(user_id)
    if not user:
        click.echo(f"User with ID {user_id} not found.")
        return
    
    # Get the token
    token = user.get_up_bank_token()
    if not token:
        click.echo("Up Bank token not found for user.")
        return
    
    click.echo(f"Testing transaction syncing for user {user.full_name} (ID: {user_id})")
    
    # Get existing transaction count
    existing_count = Transaction.query.filter_by(user_id=user_id).count()
    click.echo(f"User currently has {existing_count} transactions in the database.")
    
    # Initialize the API
    from app.api.up_bank import get_up_bank_api
    api = get_up_bank_api(token=token)
    
    # Test transaction syncing
    click.echo(f"Syncing transactions from the past {days} days...")
    created, updated = api.sync_transactions(user_id, days_back=days)
    
    # Show results
    click.echo(f"Sync completed: {created} new transactions, {updated} updated transactions")
    
    # Get new transaction count
    new_count = Transaction.query.filter_by(user_id=user_id).count()
    click.echo(f"User now has {new_count} transactions in the database.")
    
    # Show some transaction details if verbose
    if verbose and created > 0:
        click.echo("\nMost recent transactions:")
        transactions = Transaction.query.filter_by(user_id=user_id).order_by(
            Transaction.date.desc()
        ).limit(5).all()
        
        for tx in transactions:
            click.echo(f"  Date: {tx.date}")
            click.echo(f"  Description: {tx.description}")
            click.echo(f"  Amount: {tx.amount}")
            click.echo(f"  Source: {tx.source.value}")
            click.echo("  ------------------------------")

def register_upbank_commands(app):
    """Register Up Bank CLI commands with the Flask application."""
    app.cli.add_command(connect_up_bank_command)
    app.cli.add_command(sync_up_bank_command)
    app.cli.add_command(test_upbank_auth_command)
    app.cli.add_command(test_get_accounts_command)
    app.cli.add_command(test_sync_transactions_command)
