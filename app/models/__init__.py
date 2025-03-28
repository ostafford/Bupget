"""
Models package initialization.

This module imports all models to make them available when importing from the models package.
"""

# Import the models in an order that resolves the dependencies
from app.models.user import User
from app.models.account import Account, AccountType, AccountSource, AccountBalanceHistory
from app.models.transaction import Transaction, TransactionSource, TransactionCategory, WeeklySummary
from app.models.recurring import RecurringExpense, RecurringExpenseHistory, FrequencyType
from app.models.forecast import TargetDateForecast, MonthlyForecast

# Import all models here so they're available when importing from the models package
__all__ = [
    'User',
    'Account', 'AccountType', 'AccountSource', 'AccountBalanceHistory',
    'Transaction', 'TransactionSource', 'TransactionCategory', 'WeeklySummary',
    'RecurringExpense', 'RecurringExpenseHistory', 'FrequencyType',
    'TargetDateForecast', 'MonthlyForecast'
]
