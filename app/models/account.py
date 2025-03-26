"""
Account models.

This module defines the database models for financial accounts,
including bank accounts and credit cards with interest tracking.
"""

from datetime import datetime
import enum

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import func

from app.extensions import db


class AccountType(enum.Enum):
    """Enumeration of possible account types."""
    CHECKING = 'checking'      # Standard transaction account
    SAVINGS = 'savings'        # Savings account
    CREDIT_CARD = 'credit'     # Credit card account
    LOAN = 'loan'              # Loan account
    INVESTMENT = 'investment'  # Investment account


class AccountSource(enum.Enum):
    """Enumeration of possible account data sources."""
    MANUAL = 'manual'    # Manually entered by user
    UP_BANK = 'up_bank'  # Connected via Up Bank API


class Account(db.Model):
    """
    Model for financial accounts.
    
    This represents bank accounts, credit cards, and other financial accounts
    that a user might have. For credit cards, includes interest tracking.
    """
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # External ID (for accounts from Up Bank)
    external_id = db.Column(db.String(100), nullable=True, unique=True)
    
    # Account details
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.Enum(AccountType), nullable=False)
    source = db.Column(db.Enum(AccountSource), nullable=False)
    
    # Current balance
    balance = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='AUD')
    
    # Credit card specific fields
    # These are only relevant if type is CREDIT_CARD
    credit_limit = db.Column(db.Numeric(10, 2), nullable=True)
    interest_rate = db.Column(db.Numeric(5, 2), nullable=True)  # Annual percentage rate
    payment_due_date = db.Column(db.Date, nullable=True)
    minimum_payment = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Which user owns this account
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', back_populates='accounts')
    
    # Transactions associated with this account
    transactions = db.relationship('Transaction', back_populates='account')
    
    # Account balance history
    balance_history = db.relationship('AccountBalanceHistory', 
                                     back_populates='account',
                                     order_by='desc(AccountBalanceHistory.date)')
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced = db.Column(db.DateTime, nullable=True)
    
    # Optional notes
    notes = db.Column(db.Text, nullable=True)
    
    # Is this account active?
    is_active = db.Column(db.Boolean, default=True)
    
    # Is this account included in calculations?
    include_in_calculations = db.Column(db.Boolean, default=True)
    
    @hybrid_property
    def available_balance(self):
        """
        Calculate available balance.
        
        For credit cards, this is credit_limit - balance.
        For other accounts, this is just the balance.
        """
        if self.type == AccountType.CREDIT_CARD and self.credit_limit is not None:
            return self.credit_limit - self.balance
        return self.balance
    
    @hybrid_property
    def is_credit_card(self):
        """Check if this account is a credit card."""
        return self.type == AccountType.CREDIT_CARD
    
    def __repr__(self):
        """String representation of the account."""
        return f'<Account {self.name}: ${self.balance}>'
    
    def update_balance(self, new_balance, record_history=True):
        """
        Update the account balance and optionally record history.
        
        Args:
            new_balance: The new balance for this account
            record_history: Whether to record this change in the balance history
            
        Returns:
            The updated account instance
        """
        # Record history if requested
        if record_history:
            history = AccountBalanceHistory(
                account_id=self.id,
                date=datetime.utcnow().date(),
                balance=self.balance
            )
            db.session.add(history)
        
        # Update the balance
        self.balance = new_balance
        self.updated_at = datetime.utcnow()
        
        db.session.commit()
        return self
    
    def calculate_interest(self):
        """
        Calculate monthly interest for credit cards.
        
        Returns:
            The calculated interest amount, or None if not applicable
        """
        if not self.is_credit_card or self.interest_rate is None:
            return None
            
        # Calculate monthly interest (APR / 12)
        monthly_rate = self.interest_rate / 12 / 100
        interest = self.balance * monthly_rate
        
        return interest


class AccountBalanceHistory(db.Model):
    """
    Model for tracking account balance history.
    
    This allows showing balance trends over time and providing
    historical context for forecasting.
    """
    __tablename__ = 'account_balance_history'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to the account
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    account = db.relationship('Account', back_populates='balance_history')
    
    # Balance snapshot
    date = db.Column(db.Date, nullable=False)
    balance = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Optional source transaction that caused this balance change
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    
    __table_args__ = (
        # One balance record per account per day
        db.UniqueConstraint('account_id', 'date', name='uix_account_date'),
    )
    
    def __repr__(self):
        """String representation of the balance history record."""
        return f'<AccountBalanceHistory {self.date}: ${self.balance}>'
    
    @classmethod
    def get_history_for_period(cls, account_id, start_date, end_date):
        """
        Get balance history for an account over a specified period.
        
        Args:
            account_id: The account to get history for
            start_date: Start of the period
            end_date: End of the period
            
        Returns:
            List of AccountBalanceHistory objects in date order
        """
        return cls.query.filter(
            cls.account_id == account_id,
            cls.date >= start_date,
            cls.date <= end_date
        ).order_by(cls.date).all()
