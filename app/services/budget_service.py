"""
Budget service module.

This module provides functions for budget calculations, tracking, and analysis.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models import Transaction, TransactionCategory, RecurringExpense

# Configure logging
logger = logging.getLogger(__name__)

def calculate_budget_summary(user_id, start_date, end_date):
    """
    Calculate budget summary for a date range.
    
    Args:
        user_id (int): The user ID
        start_date (date): Start of the period
        end_date (date): End of the period
        
    Returns:
        dict: Budget summary with totals and category breakdowns
    """
    # Get all transactions in the date range
    transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).all()
    
    # Calculate totals
    income = sum(tx.amount for tx in transactions if tx.amount > 0)
    expenses = sum(tx.amount for tx in transactions if tx.amount < 0)
    net = income + expenses  # Note: expenses are negative
    
    # Group by category
    category_totals = db.session.query(
        TransactionCategory.id,
        TransactionCategory.name,
        func.sum(Transaction.amount).label('total')
    ).join(
        Transaction,
        Transaction.category_id == TransactionCategory.id
    ).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).group_by(
        TransactionCategory.id,
        TransactionCategory.name
    ).all()
    
    # Format category totals
    categories = [
        {
            'id': cat.id,
            'name': cat.name,
            'amount': float(cat.total)
        }
        for cat in category_totals
    ]
    
    # Return summary
    return {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'income': float(income),
        'expenses': float(expenses),
        'net': float(net),
        'categories': categories
    }

def calculate_monthly_budget(user_id, year, month):
    """
    Calculate budget summary for a specific month.
    
    Args:
        user_id (int): The user ID
        year (int): Year
        month (int): Month (1-12)
        
    Returns:
        dict: Monthly budget summary
    """
    from calendar import monthrange
    
    # Calculate start and end dates for the month
    days_in_month = monthrange(year, month)[1]
    start_date = datetime(year, month, 1).date()
    end_date = datetime(year, month, days_in_month).date()
    
    # Get budget summary for the month
    return calculate_budget_summary(user_id, start_date, end_date)

def get_upcoming_expenses(user_id, days=30):
    """
    Get upcoming recurring expenses for a user.
    
    Args:
        user_id (int): The user ID
        days (int): Number of days to look ahead
        
    Returns:
        list: Upcoming expenses sorted by date
    """
    from app.models import RecurringExpense
    
    # Calculate date range
    today = datetime.now().date()
    end_date = today + timedelta(days=days)
    
    # Get active recurring expenses
    recurring_expenses = RecurringExpense.query.filter(
        RecurringExpense.user_id == user_id,
        RecurringExpense.is_active == True,
        RecurringExpense.next_date <= end_date
    ).all()
    
    # Format results
    upcoming = [
        {
            'id': expense.id,
            'name': expense.name,
            'amount': float(expense.amount),
            'date': expense.next_date.isoformat(),
            'frequency': expense.frequency.value
        }
        for expense in recurring_expenses
    ]
    
    # Sort by date
    upcoming.sort(key=lambda x: x['date'])
    
    return upcoming

def compare_budget_vs_actual(user_id, year, month):
    """
    Compare budgeted amounts vs. actual spending for a month.
    
    This is a placeholder function that currently just returns actual spending.
    In a real implementation, it would compare against budget categories set by the user.
    
    Args:
        user_id (int): The user ID
        year (int): Year
        month (int): Month (1-12)
        
    Returns:
        dict: Budget comparison data
    """
    # For now, just return actual spending
    monthly_data = calculate_monthly_budget(user_id, year, month)
    
    # In the future, this would compare against budget targets
    return {
        'month': f"{year}-{month:02d}",
        'actuals': monthly_data,
        'comparison': {
            'income': {
                'target': 0,  # Placeholder
                'actual': monthly_data['income'],
                'difference': monthly_data['income']
            },
            'expenses': {
                'target': 0,  # Placeholder
                'actual': monthly_data['expenses'],
                'difference': monthly_data['expenses']
            }
        }
    }
