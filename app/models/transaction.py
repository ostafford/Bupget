"""
Transaction and weekly summary models.

This module defines the database models for daily transactions,
transaction categories, and weekly summaries that align with
the Monday-Sunday calendar view from the spreadsheet.
"""

from datetime import datetime, timedelta
import enum

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import func, and_, or_, case

from app.extensions import db


class TransactionSource(enum.Enum):
    """Enumeration of possible transaction sources."""
    MANUAL = 'manual'        # Manually entered by user
    UP_BANK = 'up_bank'      # Imported from Up Bank API
    RECURRING = 'recurring'   # Generated from recurring expense


class TransactionCategory(db.Model):
    """
    Model for transaction categories.
    
    Categories allow grouping transactions for reporting and analysis,
    similar to the "Groceries / Take Out" categories in the spreadsheet.
    """
    __tablename__ = 'transaction_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    # Optional color for display in UI (hex color code)
    color = db.Column(db.String(7), nullable=True)
    
    # Icon name (can be used with an icon library like FontAwesome)
    icon = db.Column(db.String(50), nullable=True)
    
    # Which user owns this category
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', back_populates='categories')
    
    # Transactions with this category
    transactions = db.relationship('Transaction', back_populates='category')
    
    def __repr__(self):
        """String representation of the category."""
        return f'<TransactionCategory {self.name}>'
    
    @classmethod
    def get_or_create(cls, name, user_id, color=None, icon=None):
        """
        Get an existing category or create a new one if it doesn't exist.
        
        Args:
            name: Category name
            user_id: User who owns this category
            color: Optional color code
            icon: Optional icon name
            
        Returns:
            The existing or newly created category
        """
        category = cls.query.filter_by(name=name, user_id=user_id).first()
        
        if category is None:
            category = cls(
                name=name,
                user_id=user_id,
                color=color,
                icon=icon
            )
            db.session.add(category)
            db.session.commit()
            
        return category


class Transaction(db.Model):
    """
    Model for individual financial transactions.
    
    This corresponds to the daily entries in the spreadsheet calendar.
    Negative amounts represent expenses, positive amounts represent income.
    """
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # External ID (for transactions from Up Bank)
    external_id = db.Column(db.String(100), nullable=True, unique=True)
    
    # Transaction details
    date = db.Column(db.Date, nullable=False, index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    
    # Is this an "Extra" transaction? (separate column in spreadsheet)
    is_extra = db.Column(db.Boolean, default=False)
    
    # Source of this transaction
    source = db.Column(db.Enum(TransactionSource), nullable=False)
    
    # Optional link to recurring expense
    recurring_expense_id = db.Column(
        db.Integer, db.ForeignKey('recurring_expenses.id'), nullable=True
    )
    recurring_expense = db.relationship('RecurringExpense')
    
    # Category for grouping transactions
    category_id = db.Column(
        db.Integer, db.ForeignKey('transaction_categories.id'), nullable=True
    )
    category = db.relationship('TransactionCategory', back_populates='transactions')
    
    # Which user owns this transaction
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', back_populates='transactions')
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional notes
    notes = db.Column(db.Text, nullable=True)
    
    # Which account this transaction is associated with (if any)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    account = db.relationship('Account', back_populates='transactions')
    
    # Weekly summary this transaction belongs to
    @hybrid_property
    def week_start_date(self):
        """Calculate the Monday of the week this transaction belongs to."""
        # Get day of week (0 is Monday in Python's datetime)
        weekday = self.date.weekday()
        # Calculate the Monday of this week
        return self.date - timedelta(days=weekday)
        
    def __repr__(self):
        """String representation of the transaction."""
        return f'<Transaction {self.date}: ${self.amount} - {self.description}>'
    
    @classmethod
    def get_by_week(cls, user_id, start_date):
        """
        Get all transactions for a specific week.
        
        Args:
            user_id: User who owns the transactions
            start_date: Monday of the week
            
        Returns:
            List of Transaction objects for that week
        """
        # Calculate end of week (Sunday)
        end_date = start_date + timedelta(days=6)
        
        return cls.query.filter(
            cls.user_id == user_id,
            cls.date >= start_date,
            cls.date <= end_date
        ).order_by(cls.date, cls.id).all()
    
    @classmethod
    def get_by_day(cls, user_id, date):
        """
        Get all transactions for a specific day.
        
        Args:
            user_id: User who owns the transactions
            date: The date to get transactions for
            
        Returns:
            List of Transaction objects for that day
        """
        return cls.query.filter_by(
            user_id=user_id,
            date=date
        ).order_by(cls.id).all()


class WeeklySummary(db.Model):
    """
    Model for weekly financial summaries.
    
    This corresponds to the EOW (End of Week) calculations in the spreadsheet.
    """
    __tablename__ = 'weekly_summaries'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Monday of this week
    week_start_date = db.Column(db.Date, nullable=False, index=True)
    
    # User who owns this summary
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', back_populates='weekly_summaries')
    
    # Calculated totals
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    total_expenses = db.Column(db.Numeric(10, 2), nullable=False)
    total_income = db.Column(db.Numeric(10, 2), nullable=False)
    total_extras = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Category-specific totals (JSON blob with category_id: amount)
    category_totals = db.Column(db.JSON, nullable=True)
    
    # When this summary was last calculated
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        # Ensure each user has only one summary per week
        db.UniqueConstraint('user_id', 'week_start_date', name='uix_user_week'),
    )
    
    def __repr__(self):
        """String representation of the weekly summary."""
        return f'<WeeklySummary {self.week_start_date}: ${self.total_amount}>'
    
    @classmethod
    def calculate_for_week(cls, user_id, start_date):
        """
        Calculate (or recalculate) the weekly summary for a given week.
        
        Args:
            user_id: User who owns the transactions
            start_date: Monday of the week
            
        Returns:
            The calculated WeeklySummary object
        """
        # Calculate end of week (Sunday)
        end_date = start_date + timedelta(days=6)
        
        # Query for transactions in this week
        transactions = Transaction.query.filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).all()
        
        # Calculate totals
        total_amount = sum(t.amount for t in transactions)
        total_expenses = sum(t.amount for t in transactions if t.amount < 0)
        total_income = sum(t.amount for t in transactions if t.amount > 0)
        total_extras = sum(t.amount for t in transactions if t.is_extra)
        
        # Calculate category totals
        category_totals = {}
        for t in transactions:
            if t.category_id:
                category_id = str(t.category_id)  # Convert to string for JSON
                if category_id not in category_totals:
                    category_totals[category_id] = 0
                category_totals[category_id] += float(t.amount)
        
        # Get or create weekly summary
        summary = cls.query.filter_by(
            user_id=user_id,
            week_start_date=start_date
        ).first()
        
        if summary is None:
            summary = cls(
                user_id=user_id,
                week_start_date=start_date
            )
            db.session.add(summary)
        
        # Update summary with calculated values
        summary.total_amount = total_amount
        summary.total_expenses = total_expenses
        summary.total_income = total_income
        summary.total_extras = total_extras
        summary.category_totals = category_totals
        summary.calculated_at = datetime.utcnow()
        
        db.session.commit()
        return summary
