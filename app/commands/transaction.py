"""
Transaction management commands.

This module provides commands for managing and analyzing transactions.
"""

import click
from datetime import datetime, timedelta
from flask.cli import with_appcontext

@click.command('transaction-stats')
@click.argument('user_id', type=int)
@click.option('--days', default=30, help='Number of days to analyze')
@with_appcontext
def transaction_stats_command(user_id, days):
    """
    Show transaction statistics for a user.
    
    Args:
        user_id: The user ID
        days: Number of days to analyze
    """
    from app.services.transaction_service import get_transaction_stats
    from app.models import User
    
    # Get the user
    user = User.query.get(user_id)
    if not user:
        click.echo(f"User with ID {user_id} not found.")
        return
    
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    click.echo(f"Transaction statistics for {user.full_name} from {start_date} to {end_date}:")
    
    # Get statistics
    stats = get_transaction_stats(user_id, start_date, end_date)
    
    # Display statistics
    click.echo(f"Total transactions: {stats['total_transactions']}")
    click.echo(f"Total income: ${stats['income']:.2f}")
    click.echo(f"Total expenses: ${stats['expenses']:.2f}")
    click.echo(f"Net: ${stats['net']:.2f}")
    click.echo(f"Extra expenses: ${stats['extras']:.2f}")
    
    if stats['top_expense_categories']:
        click.echo("\nTop expense categories:")
        for cat in stats['top_expense_categories']:
            click.echo(f"  {cat['name']}: ${abs(cat['amount']):.2f}")

@click.command('categorize-transactions')
@click.argument('user_id', type=int)
@click.option('--all/--uncategorized-only', default=False, help='Categorize all or only uncategorized transactions')
@with_appcontext
def categorize_transactions_command(user_id, all):
    """
    Auto-categorize transactions for a user.
    
    Args:
        user_id: The user ID
        all: Whether to categorize all transactions or only uncategorized ones
    """
    from app.services.transaction_service import categorize_transactions
    from app.models import User, Transaction
    
    # Get the user
    user = User.query.get(user_id)
    if not user:
        click.echo(f"User with ID {user_id} not found.")
        return
    
    # Count uncategorized transactions
    uncategorized_count = Transaction.query.filter_by(
        user_id=user_id,
        category_id=None
    ).count()
    
    click.echo(f"User {user.full_name} has {uncategorized_count} uncategorized transactions.")
    
    # Categorize transactions
    count = categorize_transactions(user_id, not all)
    
    click.echo(f"Categorized {count} transactions.")

@click.command('search-transactions')
@click.argument('user_id', type=int)
@click.argument('search_term')
@click.option('--limit', default=10, help='Maximum number of results')
@with_appcontext
def search_transactions_command(user_id, search_term, limit):
    """
    Search for transactions by description.
    
    Args:
        user_id: The user ID
        search_term: Text to search for
        limit: Maximum number of results
    """
    from app.services.transaction_service import search_transactions
    from app.models import User
    
    # Get the user
    user = User.query.get(user_id)
    if not user:
        click.echo(f"User with ID {user_id} not found.")
        return
    
    click.echo(f"Searching for '{search_term}' in transactions for {user.full_name}...")
    
    # Search transactions
    transactions = search_transactions(user_id, search_term, limit)
    
    if not transactions:
        click.echo("No matching transactions found.")
        return
    
    click.echo(f"Found {len(transactions)} matching transactions:")
    
    for tx in transactions:
        category = "Uncategorized"
        if tx.category_id and tx.category:
            category = tx.category.name
            
        date_str = tx.date.strftime("%Y-%m-%d")
        
        click.echo(f"  {date_str} | {tx.description[:40]:<40} | ${tx.amount:.2f} | {category}")

@click.command('list-categories')
@click.argument('user_id', type=int)
@with_appcontext
def list_categories_command(user_id):
    """
    List transaction categories for a user.
    
    Args:
        user_id: The user ID
    """
    from app.models import User, TransactionCategory, Transaction
    
    # Get the user
    user = User.query.get(user_id)
    if not user:
        click.echo(f"User with ID {user_id} not found.")
        return
    
    # Get categories
    categories = TransactionCategory.query.filter_by(user_id=user_id).order_by(TransactionCategory.name).all()
    
    if not categories:
        click.echo(f"No categories found for user {user.full_name}.")
        return
    
    click.echo(f"Categories for {user.full_name}:")
    
    for cat in categories:
        # Count transactions with this category
        count = Transaction.query.filter_by(
            user_id=user_id,
            category_id=cat.id
        ).count()
        
        color_str = f" ({cat.color})" if cat.color else ""
        click.echo(f"  {cat.id}: {cat.name}{color_str} - {count} transactions")

@click.command('create-category')
@click.argument('user_id', type=int)
@click.argument('name')
@click.option('--color', help='Color for the category (hex code)')
@with_appcontext
def create_category_command(user_id, name, color):
    """
    Create a new transaction category.
    
    Args:
        user_id: The user ID
        name: Category name
        color: Optional color (hex code)
    """
    from app.extensions import db
    from app.models import User, TransactionCategory
    
    # Get the user
    user = User.query.get(user_id)
    if not user:
        click.echo(f"User with ID {user_id} not found.")
        return
    
    # Check if category already exists
    existing = TransactionCategory.query.filter_by(
        user_id=user_id,
        name=name
    ).first()
    
    if existing:
        click.echo(f"Category '{name}' already exists for user {user.full_name}.")
        return
    
    # Create the category
    category = TransactionCategory(
        name=name,
        color=color,
        user_id=user_id
    )
    
    db.session.add(category)
    db.session.commit()
    
    click.echo(f"Created category '{name}' for user {user.full_name}.")

@click.command('category-summary')
@click.argument('user_id', type=int)
@click.option('--days', default=30, help='Number of days to analyze')
@with_appcontext
def category_summary_command(user_id, days):
    """
    Show transaction summary by category for a user.
    
    Args:
        user_id: The user ID
        days: Number of days to analyze
    """
    from app.services.transaction_service import group_transactions_by_category
    from app.models import User
    
    # Get the user
    user = User.query.get(user_id)
    if not user:
        click.echo(f"User with ID {user_id} not found.")
        return
    
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    click.echo(f"Category summary for {user.full_name} from {start_date} to {end_date}:")
    
    # Get categories with totals
    categories = group_transactions_by_category(user_id, start_date, end_date)
    
    if not categories:
        click.echo("No categorized transactions found.")
        return
    
    # Display expenses (negative amounts)
    expenses = [cat for cat in categories if cat['amount'] < 0]
    if expenses:
        click.echo("\nExpenses by category:")
        for cat in expenses:
            click.echo(f"  {cat['name']}: ${abs(cat['amount']):.2f} ({cat['count']} transactions)")
    
    # Display income (positive amounts)
    income = [cat for cat in categories if cat['amount'] > 0]
    if income:
        click.echo("\nIncome by category:")
        for cat in income:
            click.echo(f"  {cat['name']}: ${cat['amount']:.2f} ({cat['count']} transactions)")

def register_transaction_commands(app):
    """Register transaction CLI commands with the Flask application."""
    app.cli.add_command(transaction_stats_command)
    app.cli.add_command(categorize_transactions_command)
    app.cli.add_command(search_transactions_command)
    app.cli.add_command(list_categories_command)
    app.cli.add_command(create_category_command)
    app.cli.add_command(category_summary_command)
