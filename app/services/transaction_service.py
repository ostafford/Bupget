"""
Transaction service module.

This module provides functions for managing transactions, including
categorization, filtering, and analysis.
"""

import logging
import re
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import func, and_, or_, desc, text
from app.extensions import db
from app.models import Transaction, TransactionCategory, User, Account, TransactionSource

# Configure logging
logger = logging.getLogger(__name__)

def get_transaction_by_id(transaction_id, user_id):
    """
    Get a transaction by ID for a specific user.
    
    Args:
        transaction_id (int): The transaction ID
        user_id (int): The user ID
        
    Returns:
        Transaction: The transaction or None if not found
    """
    return Transaction.query.filter_by(
        id=transaction_id,
        user_id=user_id
    ).first()

def get_transactions_by_date_range(user_id, start_date, end_date, 
                                  category_id=None, account_id=None, 
                                  min_amount=None, max_amount=None, 
                                  is_extra=None, keywords=None,
                                  page=1, per_page=25):
    """
    Get transactions within a date range with optional filtering.
    
    Args:
        user_id (int): The user ID
        start_date (date): Start of date range
        end_date (date): End of date range
        category_id (int, optional): Filter by category ID
        account_id (int, optional): Filter by account ID
        min_amount (float, optional): Minimum transaction amount
        max_amount (float, optional): Maximum transaction amount
        is_extra (bool, optional): Filter by 'extra' flag
        keywords (str, optional): Keywords to search in descriptions
        page (int, optional): Page number for pagination
        per_page (int, optional): Items per page
        
    Returns:
        dict: Containing transactions and pagination metadata
    """
    # Start building the query
    query = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    )
    
    # Apply optional filters
    if category_id is not None:
        query = query.filter(Transaction.category_id == category_id)
        
    if account_id is not None:
        query = query.filter(Transaction.account_id == account_id)
        
    if min_amount is not None:
        query = query.filter(Transaction.amount >= min_amount)
        
    if max_amount is not None:
        query = query.filter(Transaction.amount <= max_amount)
        
    if is_extra is not None:
        query = query.filter(Transaction.is_extra == is_extra)
        
    if keywords:
        search_terms = [f"%{term}%" for term in keywords.split()]
        search_filters = []
        for term in search_terms:
            search_filters.append(Transaction.description.ilike(term))
        query = query.filter(or_(*search_filters))
    
    # Order by date (most recent first) and then by ID
    query = query.order_by(Transaction.date.desc(), Transaction.id.desc())
    
    # Execute with pagination
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Format the response
    return {
        "transactions": paginated.items,
        "total": paginated.total,
        "pages": paginated.pages,
        "page": paginated.page,
        "per_page": paginated.per_page,
        "has_next": paginated.has_next,
        "has_prev": paginated.has_prev
    }

def get_transaction_stats(user_id, start_date, end_date):
    """
    Get transaction statistics for a date range.
    
    Args:
        user_id (int): The user ID
        start_date (date): Start of date range
        end_date (date): End of date range
        
    Returns:
        dict: Transaction statistics
    """
    # Get all transactions in the date range
    transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).all()
    
    # Calculate statistics
    total_transactions = len(transactions)
    income = sum(tx.amount for tx in transactions if tx.amount > 0)
    expenses = sum(tx.amount for tx in transactions if tx.amount < 0)
    net = income + expenses  # expenses are negative, so we add
    extras = sum(tx.amount for tx in transactions if tx.is_extra)
    
    # Get top categories
    category_totals = db.session.query(
        TransactionCategory.name,
        func.sum(Transaction.amount).label('total')
    ).join(
        Transaction, 
        Transaction.category_id == TransactionCategory.id
    ).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.amount < 0  # Only expenses
    ).group_by(
        TransactionCategory.name
    ).order_by(
        func.sum(Transaction.amount)
    ).limit(5).all()
    
    return {
        "total_transactions": total_transactions,
        "income": float(income),
        "expenses": float(expenses),
        "net": float(net),
        "extras": float(extras),
        "top_expense_categories": [
            {"name": cat.name, "amount": float(cat.total)} 
            for cat in category_totals
        ]
    }

def categorize_transactions(user_id=None, uncategorized_only=True):
    """
    Auto-categorize transactions for a user.
    
    Args:
        user_id (int, optional): The user ID or None for all users
        uncategorized_only (bool): Only categorize transactions without a category
        
    Returns:
        int: Number of transactions categorized
    """
    # Build the query
    query = Transaction.query
    
    if user_id:
        query = query.filter(Transaction.user_id == user_id)
    
    if uncategorized_only:
        query = query.filter(Transaction.category_id.is_(None))
    
    transactions = query.all()
    count = 0
    
    for tx in transactions:
        category_id = suggest_category_for_transaction(tx.description, tx.user_id)
        if category_id:
            tx.category_id = category_id
            count += 1
    
    if count > 0:
        db.session.commit()
    
    return count

def mark_transaction_as_extra(transaction_id, user_id, is_extra=True):
    """
    Mark a transaction as an "extra" expense.
    
    Args:
        transaction_id (int): The transaction ID
        user_id (int): The user ID
        is_extra (bool): Whether to mark as extra or not
        
    Returns:
        bool: True if successful, False otherwise
    """
    transaction = get_transaction_by_id(transaction_id, user_id)
    
    if not transaction:
        return False
    
    transaction.is_extra = is_extra
    db.session.commit()
    
    return True

def get_recent_transactions(user_id, limit=10):
    """
    Get the most recent transactions for a user.
    
    Args:
        user_id (int): The user ID
        limit (int): Maximum number of transactions to return
        
    Returns:
        list: Recent Transaction objects
    """
    return Transaction.query.filter_by(user_id=user_id).order_by(
        Transaction.date.desc(), Transaction.id.desc()
    ).limit(limit).all()

def search_transactions(user_id, search_term, limit=50):
    """
    Search for transactions by description.
    
    Args:
        user_id (int): The user ID
        search_term (str): Text to search for
        limit (int): Maximum number of results
        
    Returns:
        list: Matching Transaction objects
    """
    return Transaction.query.filter_by(
        user_id=user_id
    ).filter(
        Transaction.description.ilike(f"%{search_term}%")
    ).order_by(
        Transaction.date.desc()
    ).limit(limit).all()

def add_manual_transaction(user_id, date, amount, description, account_id=None, 
                         category_id=None, is_extra=False, notes=None):
    """
    Add a manual transaction for a user.
    
    Args:
        user_id (int): The user ID
        date (date): Transaction date
        amount (float): Transaction amount
        description (str): Transaction description
        account_id (int, optional): Account ID
        category_id (int, optional): Category ID
        is_extra (bool): Whether this is an "extra" expense
        notes (str, optional): Additional notes
        
    Returns:
        Transaction: The created transaction
    """
    # Create the transaction
    transaction = Transaction(
        date=date,
        amount=amount,
        description=description,
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        is_extra=is_extra,
        notes=notes,
        source=TransactionSource.MANUAL,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.session.add(transaction)
    
    # If account_id is provided, update the account balance
    if account_id:
        account = Account.query.get(account_id)
        if account:
            account.balance += amount
            account.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    # Update weekly summary
    from app.models.transaction import WeeklySummary
    WeeklySummary.calculate_for_week(user_id, transaction.week_start_date)
    
    return transaction

def update_transaction(transaction_id, user_id, **kwargs):
    """
    Update an existing transaction.
    
    Args:
        transaction_id (int): The transaction ID
        user_id (int): The user ID
        **kwargs: Fields to update
        
    Returns:
        Transaction: The updated transaction or None if not found
    """
    transaction = get_transaction_by_id(transaction_id, user_id)
    
    if not transaction:
        return None
    
    # Track if we need to update the account balance
    old_amount = transaction.amount
    old_account_id = transaction.account_id
    
    # Update fields
    for key, value in kwargs.items():
        if hasattr(transaction, key):
            setattr(transaction, key, value)
    
    transaction.updated_at = datetime.utcnow()
    
    # Update account balance if amount or account changed
    if 'amount' in kwargs or 'account_id' in kwargs:
        # If account changed, update old and new account balances
        if 'account_id' in kwargs and old_account_id != kwargs['account_id']:
            # Revert change to old account
            if old_account_id:
                old_account = Account.query.get(old_account_id)
                if old_account:
                    old_account.balance -= old_amount
                    old_account.updated_at = datetime.utcnow()
            
            # Apply change to new account
            if transaction.account_id:
                new_account = Account.query.get(transaction.account_id)
                if new_account:
                    new_account.balance += transaction.amount
                    new_account.updated_at = datetime.utcnow()
        # If only amount changed, update current account
        elif 'amount' in kwargs and transaction.account_id:
            account = Account.query.get(transaction.account_id)
            if account:
                # Remove old amount and add new amount
                account.balance = account.balance - old_amount + transaction.amount
                account.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    # Update weekly summary
    from app.models.transaction import WeeklySummary
    WeeklySummary.calculate_for_week(user_id, transaction.week_start_date)
    
    return transaction

def delete_transaction(transaction_id, user_id):
    """
    Delete a transaction.
    
    Args:
        transaction_id (int): The transaction ID
        user_id (int): The user ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    transaction = get_transaction_by_id(transaction_id, user_id)
    
    if not transaction:
        return False
    
    # Store the week start date for recalculating summary
    week_start_date = transaction.week_start_date
    
    # Revert the account balance if needed
    if transaction.account_id:
        account = Account.query.get(transaction.account_id)
        if account:
            account.balance -= transaction.amount
            account.updated_at = datetime.utcnow()
    
    # Delete the transaction
    db.session.delete(transaction)
    db.session.commit()
    
    # Update weekly summary
    from app.models.transaction import WeeklySummary
    WeeklySummary.calculate_for_week(user_id, week_start_date)
    
    return True

def group_transactions_by_category(user_id, start_date, end_date):
    """
    Group transactions by category for a given date range.
    
    Args:
        user_id (int): The user ID
        start_date (date): Start of date range
        end_date (date): End of date range
        
    Returns:
        list: Categories with total amounts
    """
    # Query for category totals
    category_totals = db.session.query(
        TransactionCategory.id,
        TransactionCategory.name,
        TransactionCategory.color,
        func.sum(Transaction.amount).label('total_amount'),
        func.count(Transaction.id).label('transaction_count')
    ).outerjoin(
        Transaction, 
        and_(
            Transaction.category_id == TransactionCategory.id,
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        )
    ).filter(
        TransactionCategory.user_id == user_id
    ).group_by(
        TransactionCategory.id,
        TransactionCategory.name,
        TransactionCategory.color
    ).all()
    
    # Format the results
    results = []
    
    for cat in category_totals:
        results.append({
            'id': cat.id,
            'name': cat.name,
            'color': cat.color,
            'amount': float(cat.total_amount or 0),
            'count': cat.transaction_count
        })
    
    # Sort by amount (highest expense first)
    results.sort(key=lambda x: x['amount'])
    
    return results

def suggest_category_for_transaction(description, user_id=None):
    """
    Suggest a category for a transaction based on its description.
    
    Args:
        description (str): Transaction description
        user_id (int, optional): User ID for personalized matching
        
    Returns:
        int: Suggested category ID or None
    """
    # Normalize description
    description = description.lower()
    
    # Common category patterns
    category_patterns = {
        "groceries": [
            r'woolworths', r'coles', r'aldi', r'iga', r'foodland', r'grocery', 
            r'supermarket', r'fruit', r'vegetable'
        ],
        "dining out": [
            r'cafe', r'restaurant', r'uber eats', r'menulog', r'doordash',
            r'coffee', r'mcdonald', r'hungry jack', r'kfc'
        ],
        "transport": [
            r'uber', r'lyft', r'taxi', r'train', r'bus', r'transport', r'fuel',
            r'petrol', r'gasoline', r'parking', r'toll'
        ],
        "utilities": [
            r'water', r'electricity', r'gas', r'power', r'energy', r'internet',
            r'phone', r'mobile', r'utility'
        ],
        "entertainment": [
            r'movie', r'cinema', r'netflix', r'spotify', r'disney', r'amazon prime',
            r'entertainment', r'game', r'playstation', r'xbox', r'nintendo'
        ],
        "health": [
            r'pharmacy', r'doctor', r'hospital', r'medical', r'dental', r'gym',
            r'fitness', r'health'
        ],
        "shopping": [
            r'amazon', r'ebay', r'kmart', r'target', r'big w', r'bunnings',
            r'shopping', r'retail', r'clothing', r'apparel'
        ]
    }
    
    # First, check if we already have a similar transaction that's categorized
    if user_id:
        # Find transactions with similar descriptions, but without using the similarity function
        # Use only simple ILIKE pattern matching instead
        similar_transaction = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.category_id.isnot(None),
            Transaction.description.ilike(f"%{description}%")
        ).order_by(
            Transaction.created_at.desc()  # Order by most recent first
        ).first()
        
        if similar_transaction:
            return similar_transaction.category_id
    
    # If no similar transaction found, use pattern matching
    for category_name, patterns in category_patterns.items():
        for pattern in patterns:
            if re.search(pattern, description, re.IGNORECASE):
                # Get or create the category
                if user_id:
                    category = TransactionCategory.query.filter_by(
                        name=category_name,
                        user_id=user_id
                    ).first()
                    
                    if category:
                        return category.id
                    else:
                        # Create the category
                        new_category = TransactionCategory(
                            name=category_name,
                            user_id=user_id
                        )
                        db.session.add(new_category)
                        db.session.commit()
                        return new_category.id
    
    # No match found
    return None

def get_recurring_transactions(user_id, min_occurrences=3, date_range_days=180):
    """
    Identify potentially recurring transactions.
    
    Args:
        user_id (int): The user ID
        min_occurrences (int): Minimum number of occurrences to consider recurring
        date_range_days (int): Number of days to look back
        
    Returns:
        list: Potential recurring transaction patterns
    """
    # Calculate the date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=date_range_days)
    
    # Get transactions in the date range
    transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).order_by(Transaction.date).all()
    
    # Group similar transactions
    transaction_groups = {}
    
    for tx in transactions:
        # Skip positive transactions (income)
        if tx.amount >= 0:
            continue
        
        found_group = False
        
        # Try to match to an existing group
        for key, group in transaction_groups.items():
            # Simplified check for description similarity
            # Check if one contains the other or they're an exact match
            if (tx.description.lower() in key.lower() or 
                key.lower() in tx.description.lower() or
                tx.description.lower() == key.lower()):
                
                # Check if amount is similar (within 10%)
                if abs(abs(tx.amount) - abs(group['amount'])) < 0.1 * abs(group['amount']):
                    group['transactions'].append(tx)
                    group['dates'].append(tx.date)
                    found_group = True
                    break
        
        # If no matching group, create a new one
        if not found_group:
            transaction_groups[tx.description] = {
                'amount': tx.amount,
                'transactions': [tx],
                'dates': [tx.date]
            }
    
    # Filter groups with enough occurrences
    recurring = []
    
    for description, group in transaction_groups.items():
        if len(group['transactions']) >= min_occurrences:
            # Calculate average time between transactions
            dates = sorted(group['dates'])
            intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
            
            if not intervals:
                continue
                
            avg_interval = sum(intervals) / len(intervals)
            
            # Check if intervals are regular
            regular_intervals = all(abs(interval - avg_interval) <= 5 for interval in intervals)
            
            # Determine frequency
            frequency = None
            if regular_intervals:
                if 25 <= avg_interval <= 35:
                    frequency = "MONTHLY"
                elif 13 <= avg_interval <= 16:
                    frequency = "FORTNIGHTLY"
                elif 6 <= avg_interval <= 8:
                    frequency = "WEEKLY"
                elif 89 <= avg_interval <= 93:
                    frequency = "QUARTERLY"
                elif 355 <= avg_interval <= 370:
                    frequency = "YEARLY"
            
            # Add to results
            recurring.append({
                'description': description,
                'amount': float(group['amount']),
                'occurrences': len(group['transactions']),
                'last_date': max(dates),
                'avg_interval_days': avg_interval,
                'suspected_frequency': frequency
            })
    
    return recurring

def process_upbank_transaction(transaction_data, user_id, account_map=None):
    """
    Process a transaction from the Up Bank API.
    
    Args:
        transaction_data (dict): Transaction data from Up Bank API
        user_id (int): User ID to assign the transaction to
        account_map (dict, optional): Map of external account IDs to internal account IDs
            
    Returns:
        tuple: (status, transaction_obj, is_new) 
               where status is "created", "updated", or None if failed
    """
    from datetime import datetime
    from app.models import Transaction, TransactionSource, Account
    from app.extensions import db
    
    # Extract the transaction ID
    tx_id = transaction_data.get('id')
    if not tx_id:
        logger.error("Transaction ID not found in data")
        return None, None, False
    
    # Extract transaction details from attributes
    attributes = transaction_data.get('attributes', {})
    
    # Get transaction description
    description = attributes.get('description', 'Unknown transaction')
    
    # Try to get a more meaningful description
    if 'rawText' in attributes and attributes['rawText']:
        description = attributes['rawText']
    
    # Extract date
    created_at = attributes.get('createdAt')
    if not created_at:
        logger.error("Transaction date not found")
        return None, None, False
        
    try:
        tx_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
    except (ValueError, TypeError, AttributeError):
        tx_date = datetime.now().date()
    
    # Extract amount
    amount_data = attributes.get('amount', {})
    value = amount_data.get('value', '0')
    
    try:
        amount = float(value)
    except (ValueError, TypeError):
        amount = 0.0
    
    # Determine account ID
    account_id = None
    
    # If account_map not provided, try to determine account from relationships
    if account_map is None:
        account_map = {}
        relationships = transaction_data.get('relationships', {})
        account_data = relationships.get('account', {}).get('data', {})
        
        if account_data and 'id' in account_data:
            external_account_id = account_data['id']
            account = Account.query.filter_by(
                external_id=external_account_id,
                user_id=user_id
            ).first()
            
            if account:
                account_id = account.id
    else:
        # Use provided account_map
        relationships = transaction_data.get('relationships', {})
        account_data = relationships.get('account', {}).get('data', {})
        
        if account_data and 'id' in account_data:
            external_account_id = account_data['id']
            account_id = account_map.get(external_account_id)
    
    # Check if transaction already exists
    existing_tx = Transaction.query.filter_by(
        external_id=tx_id,
        user_id=user_id
    ).first()
    
    if existing_tx:
        # Update existing transaction
        existing_tx.description = description
        existing_tx.amount = amount
        existing_tx.date = tx_date
        existing_tx.account_id = account_id
        existing_tx.updated_at = datetime.utcnow()
        
        # If category not already set, try to categorize
        if not existing_tx.category_id:
            category_id = suggest_category_for_transaction(description, user_id)
            if category_id:
                existing_tx.category_id = category_id
        
        return "updated", existing_tx, False
    else:
        # Create new transaction
        # Try to categorize the transaction
        category_id = suggest_category_for_transaction(description, user_id)
        
        new_tx = Transaction(
            external_id=tx_id,
            date=tx_date,
            description=description,
            amount=amount,
            source=TransactionSource.UP_BANK,
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return "created", new_tx, True


def handle_balance_update(transaction, account=None):
    """
    Update account balance for a transaction.
    
    Args:
        transaction (Transaction): The transaction
        account (Account, optional): The account (if already loaded)
        
    Returns:
        bool: True if balance updated, False otherwise
    """
    from app.extensions import db
    from app.models import Account
    
    if not transaction.account_id:
        return False
    
    # Load account if not provided
    if account is None:
        account = Account.query.get(transaction.account_id)
        
    if not account:
        return False
    
    # Update account balance
    account.balance += transaction.amount
    account.updated_at = datetime.utcnow()
    
    return True


def save_transaction(transaction, is_new=True, update_balance=True):
    """
    Save a transaction to the database and handle related updates.
    
    Args:
        transaction (Transaction): The transaction to save
        is_new (bool): Whether this is a new transaction
        update_balance (bool): Whether to update account balance
        
    Returns:
        bool: True if successful, False otherwise
    """
    from app.extensions import db
    from app.models.transaction import WeeklySummary
    
    try:
        # Add new transaction to session if it's new
        if is_new:
            db.session.add(transaction)
        
        # Save the transaction
        db.session.commit()
        
        # Update account balance if needed
        if update_balance and transaction.account_id:
            handle_balance_update(transaction)
            db.session.commit()
        
        # Update weekly summary
        WeeklySummary.calculate_for_week(
            transaction.user_id, 
            transaction.week_start_date
        )
        
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving transaction: {str(e)}")
        return False


def process_and_save_upbank_transaction(transaction_data, user_id, account_map=None):
    """
    Process and save a transaction from Up Bank API.
    
    This is a higher-level function that combines processing and saving.
    
    Args:
        transaction_data (dict): Transaction data from Up Bank API
        user_id (int): User ID
        account_map (dict, optional): Map of external account IDs to internal account IDs
        
    Returns:
        tuple: (success, status, transaction)
    """
    # Process the transaction
    status, transaction, is_new = process_upbank_transaction(
        transaction_data, user_id, account_map
    )
    
    if not status or not transaction:
        return False, None, None
    
    # Save the transaction and handle related updates
    success = save_transaction(transaction, is_new)
    
    return success, status, transaction