"""
CLI commands for the application.

This module defines CLI commands that can be run with 'flask [command]'.
"""

import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models import User, Account, Transaction, RecurringExpense

# Initialize app variable for use in commands
app = None


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Initialize the database - create all tables."""
    # Create all tables in the database
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
    from app.models.user import User
    
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


@click.command('create-demo-user')
@with_appcontext
def create_demo_user_command():
    """Create a demo user for testing."""
    from app.models import User
    
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
    from app.models.user import User
    
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
    from app.models.user import User
    
    users = User.query.all()
    
    if not users:
        click.echo('No users found in the database.')
        return
    
    click.echo('Users in the database:')
    for user in users:
        click.echo(f'  ID: {user.id}, Email: {user.email}, Name: {user.full_name}')

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


def register_commands(app_instance):
    """Register CLI commands with the Flask application."""
    global app
    app = app_instance  # Store app reference for verify-setup command
    
    app.cli.add_command(init_db_command)
    app.cli.add_command(drop_db_command)
    app.cli.add_command(create_demo_user_command)
    app.cli.add_command(verify_setup_command)
    app.cli.add_command(connect_up_bank_command)
    app.cli.add_command(sync_up_bank_command)
    app.cli.add_command(test_upbank_auth_command)
    app.cli.add_command(generate_encryption_key_command)
    app.cli.add_command(delete_user_command)
    app.cli.add_command(list_users_command)
    app.cli.add_command(reset_db_command)
    app.cli.add_command(sync_accounts_command)
    app.cli.add_command(list_accounts_command)
    app.cli.add_command(test_sync_transactions_command)
    app.cli.add_command(test_get_accounts_command)
