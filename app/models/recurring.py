"""
Recurring expense models.

This module defines the database models for recurring expenses
with support for different frequencies and version history.
"""

from datetime import datetime
from enum import Enum

from app.extensions import db


class FrequencyType(Enum):
    """Enumeration of possible recurring expense frequencies."""
    WEEKLY = 'weekly'
    FORTNIGHTLY = 'fortnightly'
    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'
    YEARLY = 'yearly'


class RecurringExpense(db.Model):
    """
    Model representing a recurring expense.
    
    This model stores the current active version of each recurring expense.
    Historical versions are stored in the RecurringExpenseHistory model.
    """
    __tablename__ = 'recurring_expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    frequency = db.Column(db.Enum(FrequencyType), nullable=False)
    
    # The next date this expense will occur
    next_date = db.Column(db.Date, nullable=False)
    
    # When this expense should start being considered
    start_date = db.Column(db.Date, nullable=False, default=datetime.now().date)
    
    # Optional end date (for temporary expenses)
    end_date = db.Column(db.Date, nullable=True)
    
    # Is this expense currently active?
    is_active = db.Column(db.Boolean, default=True)
    
    # When was this version created
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Optional notes
    notes = db.Column(db.Text, nullable=True)
    
    # Which user owns this expense
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', back_populates='recurring_expenses')
    
    # History relationship
    history = db.relationship('RecurringExpenseHistory', 
                             back_populates='current_expense',
                             order_by='desc(RecurringExpenseHistory.effective_date)')
    
    def __repr__(self):
        """String representation of the recurring expense."""
        return f'<RecurringExpense {self.name} ({self.frequency.value}): ${self.amount}>'
    
    def create_history_record(self, old_amount=None):
        """
        Create a history record when this expense is modified.
        
        Args:
            old_amount: The previous amount before the change
                        If None, this is a new expense
        """
        # Don't create history for new expenses
        if old_amount is None:
            return
            
        history = RecurringExpenseHistory(
            current_expense_id=self.id,
            name=self.name,
            amount=old_amount,  # Store the old amount
            frequency=self.frequency,
            effective_date=datetime.utcnow()
        )
        db.session.add(history)
    
    @classmethod
    def create_new(cls, name, amount, frequency, next_date, user_id, notes=None):
        """
        Create a new recurring expense.
        
        Args:
            name: Name of the expense
            amount: Amount of the expense
            frequency: Frequency enum value
            next_date: Next occurrence date
            user_id: ID of the user who owns this expense
            notes: Optional notes
            
        Returns:
            The newly created RecurringExpense instance
        """
        expense = cls(
            name=name,
            amount=amount,
            frequency=frequency,
            next_date=next_date,
            user_id=user_id,
            notes=notes
        )
        db.session.add(expense)
        db.session.commit()
        return expense
    
    def update_amount(self, new_amount):
        """
        Update the amount of this expense and create a history record.
        
        Args:
            new_amount: The new amount for this expense
            
        Returns:
            The updated expense instance
        """
        # Create history record with the old amount
        self.create_history_record(old_amount=self.amount)
        
        # Update to the new amount
        self.amount = new_amount
        self.created_at = datetime.utcnow()
        
        db.session.commit()
        return self
    
    @classmethod
    def get_active_by_frequency(cls, user_id, frequency=None):
        """
        Get all active recurring expenses for a user, optionally filtered by frequency.
        
        Args:
            user_id: ID of the user
            frequency: Optional frequency to filter by
            
        Returns:
            List of RecurringExpense instances
        """
        query = cls.query.filter_by(user_id=user_id, is_active=True)
        
        if frequency is not None:
            query = query.filter_by(frequency=frequency)
            
        return query.order_by(cls.name).all()


class RecurringExpenseHistory(db.Model):
    """
    Model for storing the history of changes to recurring expenses.
    
    This allows tracking how expenses change over time and ensures
    that future projections use the correct amount for each time period.
    """
    __tablename__ = 'recurring_expense_history'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Link to the current version of this expense
    current_expense_id = db.Column(db.Integer, 
                               db.ForeignKey('recurring_expenses.id'), 
                               nullable=False)
    current_expense = db.relationship('RecurringExpense', back_populates='history')
    
    # Snapshot of the expense at this point in history
    name = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    frequency = db.Column(db.Enum(FrequencyType), nullable=False)
    
    # When this version was effective
    effective_date = db.Column(db.DateTime, nullable=False)
    
    def __repr__(self):
        """String representation of the expense history record."""
        return (f'<RecurringExpenseHistory {self.name} '
                f'(${self.amount}) from {self.effective_date}>')
