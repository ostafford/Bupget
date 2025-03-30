"""
CLI commands for transaction management.

These commands allow testing and working with transaction data from the command line.
"""

import click
from datetime import datetime, timedelta
from flask.cli import with_appcontext
from app.models import User, Transaction, TransactionCategory
from app.services.transaction_service import (
    categorize_transactions, get_transactions_by_date_range,
    get_transaction_stats, get_recurring_transactions,
    group_transactions_by_category
)

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
    # Get the user
    user = User.query.get(user_id)
    if not user:
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


def register_transaction_commands(app):
    """Register transaction CLI commands with the Flask application."""
    app.cli.add_command(categorize_transactions_command)
    app.cli.add_command(transaction_stats_command)
    app.cli.add_command(find_recurring_command)
    app.cli.add_command(category_summary_command)
    app.cli.add_command(search_transactions_command)
    app.cli.add_command(list_categories_command)
    app.cli.add_command(create_category_command)

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


@click.command('find-recurring')
@click.argument('user_id', type=int)
@click.option('--days', default=180, help='Number of days to analyze')
@click.option('--min-occurrences', default=3, help='Minimum occurrences to consider recurring')
@with_appcontext
def find_recurring_command(user_id, days, min_occurrences):
    """
    Find potentially recurring transactions for a user.
    
    Args:
        user_id: The user ID
        days: Number of days to analyze
        min_occurrences: Minimum occurrences to consider recurring
    """
    # Get the user
    user = User.query.get(user_id)
    if not user:
        click.echo(f"User with ID {user_id} not found.")
        return
    
    click.echo(f"Analyzing {days} days of transactions for {user.full_name}...")
    
    # Find recurring transactions
    recurring = get_recurring_transactions(
        user_id, 
        min_occurrences=min_occurrences,
        date_range_days=days
    )
    
    if not recurring:
        click.echo("No recurring transactions found.")
        return
    
    click.echo(f"Found {len(recurring)} potential recurring transactions:")
    
    for i, tx in enumerate(recurring):
        frequency = tx['suspected_frequency'] or 'IRREGULAR'
        click.echo(f"\n{i+1}. {tx['description']}")
        click.echo(f"   Amount: ${abs(tx['amount']):.2f}")
        click.echo(f"   Occurrences: {tx['occurrences']}")
        click.echo(f"   Average interval: {tx['avg_interval_days']:.1f} days")
        click.echo(f"   Suspected frequency: {frequency}")
        click.echo(f"   Last occurred: {tx['last_date']}")


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
    
    click.echo
