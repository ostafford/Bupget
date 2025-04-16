"""
Forecast service module.

This module provides functions for financial forecasting and projections.
"""

import logging
from datetime import datetime, timedelta, date
from app.extensions import db
from app.models import Account, Transaction, RecurringExpense, MonthlyForecast, TargetDateForecast

# Configure logging
logger = logging.getLogger(__name__)

def calculate_daily_balances(user_id, start_date, end_date):
    """
    Calculate projected daily balances for a date range.
    
    Args:
        user_id (int): The user ID
        start_date (date): Start date for projection
        end_date (date): End date for projection
        
    Returns:
        dict: Daily balance projections
    """
    # Get current account balances
    accounts = Account.query.filter_by(
        user_id=user_id,
        include_in_calculations=True
    ).all()
    
    # Calculate total starting balance
    starting_balance = sum(float(account.balance) for account in accounts)
    
    # Get known future transactions (e.g., scheduled transfers)
    future_transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date <= end_date
    ).order_by(Transaction.date).all()
    
    # Get recurring expenses
    recurring_expenses = RecurringExpense.query.filter_by(
        user_id=user_id,
        is_active=True
    ).all()
    
    # Generate projected recurring expense transactions
    projected_transactions = []
    for expense in recurring_expenses:
        # Skip if next occurrence is after end date
        if expense.next_date > end_date:
            continue
            
        # Add occurrences within date range
        current_date = expense.next_date
        while current_date <= end_date:
            projected_transactions.append({
                'date': current_date,
                'amount': float(expense.amount),
                'description': f"{expense.name} (Recurring)",
                'is_actual': False
            })
            
            # Calculate next date based on frequency
            if expense.frequency.value == 'WEEKLY':
                current_date = current_date + timedelta(days=7)
            elif expense.frequency.value == 'FORTNIGHTLY':
                current_date = current_date + timedelta(days=14)
            elif expense.frequency.value == 'MONTHLY':
                # Simple approximation - add 30 days
                current_date = current_date + timedelta(days=30)
            elif expense.frequency.value == 'QUARTERLY':
                # Simple approximation - add 90 days
                current_date = current_date + timedelta(days=90)
            elif expense.frequency.value == 'YEARLY':
                # Simple approximation - add 365 days
                current_date = current_date + timedelta(days=365)
            else:
                # Unknown frequency, stop after first occurrence
                break
    
    # Convert actual transactions to dictionary format
    actual_transactions = [
        {
            'date': tx.date,
            'amount': float(tx.amount),
            'description': tx.description,
            'is_actual': True
        }
        for tx in future_transactions
    ]
    
    # Combine actual and projected transactions
    all_transactions = actual_transactions + projected_transactions
    all_transactions.sort(key=lambda x: x['date'])
    
    # Calculate daily balance
    daily_balances = {}
    running_balance = starting_balance
    current_date = start_date
    
    while current_date <= end_date:
        # Get transactions for this day
        todays_transactions = [tx for tx in all_transactions if tx['date'] == current_date]
        
        # Calculate day's total
        day_total = sum(tx['amount'] for tx in todays_transactions)
        
        # Update running balance
        running_balance += day_total
        
        # Store balance for this day
        daily_balances[current_date.isoformat()] = {
            'date': current_date.isoformat(),
            'balance': running_balance,
            'transactions': todays_transactions
        }
        
        # Move to next day
        current_date = current_date + timedelta(days=1)
    
    return {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'starting_balance': starting_balance,
        'ending_balance': running_balance,
        'daily_balances': daily_balances
    }

def forecast_to_target_date(user_id, target_date, name=None):
    """
    Create a forecast for a target date.
    
    Args:
        user_id (int): The user ID
        target_date (date or str): Target date for forecast
        name (str, optional): Name for this forecast
        
    Returns:
        dict: Forecast data
    """
    # Parse target date if string
    if isinstance(target_date, str):
        target_date = datetime.fromisoformat(target_date).date()
    
    # Default name
    if name is None:
        name = f"Forecast to {target_date.isoformat()}"
    
    # Get today's date
    today = datetime.now().date()
    
    # Calculate forecast
    forecast_data = calculate_daily_balances(user_id, today, target_date)
    
    # Create or update forecast record
    forecast = TargetDateForecast.query.filter_by(
        user_id=user_id,
        target_date=target_date
    ).first()
    
    if not forecast:
        forecast = TargetDateForecast(
            name=name,
            target_date=target_date,
            user_id=user_id,
            projected_balance=forecast_data['ending_balance'],
            created_at=datetime.utcnow(),
            last_calculated=datetime.utcnow()
        )
        db.session.add(forecast)
    else:
        forecast.name = name
        forecast.projected_balance = forecast_data['ending_balance']
        forecast.last_calculated = datetime.utcnow()
    
    db.session.commit()
    
    # Add forecast ID to result
    forecast_data['forecast_id'] = forecast.id
    forecast_data['name'] = name
    
    return forecast_data

def get_forecast_summary(user_id):
    """
    Get a summary of all forecasts for a user.
    
    Args:
        user_id (int): The user ID
        
    Returns:
        dict: Summary of forecasts
    """
    # Get target date forecasts
    target_forecasts = TargetDateForecast.query.filter_by(
        user_id=user_id
    ).order_by(TargetDateForecast.target_date).all()
    
    # Format results
    return {
        'target_date_forecasts': [
            {
                'id': f.id,
                'name': f.name,
                'target_date': f.target_date.isoformat(),
                'projected_balance': float(f.projected_balance),
                'last_calculated': f.last_calculated.isoformat()
            }
            for f in target_forecasts
        ]
    }
