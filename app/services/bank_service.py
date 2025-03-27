"""
Banking service module.

This module provides higher-level functions for integrating with 
banking APIs and managing financial data.
"""

import logging
from datetime import datetime, timedelta
from flask import current_app
from app.extensions import db
from app.models import User, Account, Transaction, WeeklySummary
from app.api.up_bank import get_up_bank_api

# Configure logging
logger = logging.getLogger(__name__)


def connect_up_bank(user_id, token):
    """
    Connect a user to the Up Bank API.
    
    Args:
        user_id (int): The user ID
        token (str): The Up Bank API token
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        # Get the user
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return False
        
        # Initialize the API
        api = get_up_bank_api(token=token)
        
        # Test the connection
        if not api.ping():
            logger.error("Failed to connect to Up Bank API")
            return False
        
        # Save the token
        user.set_up_bank_token(token)
        
        # Sync initial account data
        api.sync_accounts(user_id)
        
        return True
    except Exception as e:
        logger.error(f"Error connecting to Up Bank: {str(e)}")
        return False


def sync_accounts(user_id):
    """
    Sync accounts from Up Bank for a user.
    
    Args:
        user_id (int): The user ID
        
    Returns:
        tuple: (success, message, accounts_count)
    """
    try:
        # Get the user
        user = User.query.get(user_id)
        if not user:
            return False, "User not found", 0
        
        # Get the API token
        token = user.get_up_bank_token()
        if not token:
            return False, "Up Bank token not found", 0
        
        # Initialize the API
        api = get_up_bank_api(token=token)
        
        # Sync accounts
        created, updated = api.sync_accounts(user_id)
        
        return True, f"Synced {created} new and {updated} existing accounts", created + updated
    except Exception as e:
        logger.error(f"Error syncing accounts: {str(e)}")
        return False, f"Error: {str(e)}", 0


def sync_transactions(user_id, days_back=30):
    """
    Sync transactions from Up Bank for a user.
    
    Args:
        user_id (int): The user ID
        days_back (int, optional): Number of days of history to sync
        
    Returns:
        tuple: (success, message, transaction_count)
    """
    try:
        # Get the user
        user = User.query.get(user_id)
        if not user:
            return False, "User not found", 0
        
        # Get the API token
        token = user.get_up_bank_token()
        if not token:
            return False, "Up Bank token not found", 0
        
        # Initialize the API
        api = get_up_bank_api(token=token)
        
        # Sync transactions
        created, updated = api.sync_transactions(user_id, days_back=days_back)
        
        # Update weekly summaries for affected weeks
        if created > 0 or updated > 0:
            update_weekly_summaries(user_id, days=days_back)
        
        return True, f"Synced {created} new and {updated} existing transactions", created + updated
    except Exception as e:
        logger.error(f"Error syncing transactions: {str(e)}")
        return False, f"Error: {str(e)}", 0


def update_weekly_summaries(user_id, days=30):
    """
    Update weekly summaries for a specific time period.
    
    Args:
        user_id (int): The user ID
        days (int, optional): Number of days to look back
        
    Returns:
        int: Number of summaries updated
    """
    from app.models.transaction import WeeklySummary
    
    try:
        # Calculate the date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Find all Mondays in the date range
        current_date = start_date
        mondays = []
        
        while current_date <= end_date:
            # If this is a Monday (weekday 0)
            if current_date.weekday() == 0:
                mondays.append(current_date)
            
            # Move to next day
            current_date += timedelta(days=1)
            
        # If no Mondays in the range, find the most recent Monday before the range
        if not mondays:
            current_date = start_date
            while current_date.weekday() != 0:
                current_date -= timedelta(days=1)
            mondays.append(current_date)
        
        # Calculate summary for each week
        count = 0
        for monday in mondays:
            # Calculate or recalculate the weekly summary
            summary = WeeklySummary.calculate_for_week(user_id, monday)
            if summary:
                count += 1
        
        return count
    except Exception as e:
        logger.error(f"Error updating weekly summaries: {str(e)}")
        return 0


def get_account_balance_history(account_id, days=30):
    """
    Get balance history for an account.
    
    Args:
        account_id (int): The account ID
        days (int, optional): Number of days of history
        
    Returns:
        list: List of (date, balance) tuples
    """
    from app.models.account import AccountBalanceHistory
    
    try:
        # Calculate the date range
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get the balance history records
        history = AccountBalanceHistory.get_history_for_period(
            account_id, start_date, end_date
        )
        
        # Convert to list of (date, balance) tuples
        result = [(h.date, float(h.balance)) for h in history]
        
        return result
    except Exception as e:
        logger.error(f"Error getting account balance history: {str(e)}")
        return []


def get_transactions_by_week(user_id, start_date=None, weeks=4):
    """
    Get transactions grouped by week.
    
    Args:
        user_id (int): The user ID
        start_date (date, optional): Start date (defaults to current date)
        weeks (int, optional): Number of weeks to include
        
    Returns:
        dict: Dictionary of week_start_date -> list of transactions
    """
    try:
        # Default to current date if not specified
        if start_date is None:
            start_date = datetime.now().date()
        
        # Find the Monday of the current week
        while start_date.weekday() != 0:  # 0 = Monday
            start_date -= timedelta(days=1)
        
        # Get transactions for each week
        result = {}
        
        for i in range(weeks):
            week_start = start_date - timedelta(days=7 * i)
            week_end = week_start + timedelta(days=6)
            
            # Query transactions for this week
            transactions = Transaction.query.filter(
                Transaction.user_id == user_id,
                Transaction.date >= week_start,
                Transaction.date <= week_end
            ).order_by(Transaction.date, Transaction.id).all()
            
            # Add to result
            result[week_start] = transactions
        
        return result
    except Exception as e:
        logger.error(f"Error getting transactions by week: {str(e)}")
        return {}
