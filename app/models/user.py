"""
User model.

This module defines the database model for application users.
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(db.Model, UserMixin):
    """
    Model for application users.
    
    This model includes user authentication information and preferences.
    It also establishes relationships with other models.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Authentication fields
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Personal details
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    
    # Up Bank API token (encrypted in database)
    up_bank_token = db.Column(db.String(255), nullable=True)
    
    # User preferences (stored as JSON for flexibility)
    preferences = db.Column(db.JSON, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships to other models
    accounts = db.relationship('Account', back_populates='user', cascade='all, delete-orphan')
    transactions = db.relationship('Transaction', back_populates='user', cascade='all, delete-orphan')
    recurring_expenses = db.relationship('RecurringExpense', back_populates='user', cascade='all, delete-orphan')
    categories = db.relationship('TransactionCategory', back_populates='user', cascade='all, delete-orphan')
    weekly_summaries = db.relationship('WeeklySummary', back_populates='user', cascade='all, delete-orphan')
    target_forecasts = db.relationship('TargetDateForecast', back_populates='user', cascade='all, delete-orphan')
    monthly_forecasts = db.relationship('MonthlyForecast', back_populates='user', cascade='all, delete-orphan')
    
    def __repr__(self):
        """String representation of the user."""
        return f'<User {self.email}>'
    
    @property
    def password(self):
        """Password getter raises an error - password should not be readable."""
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        """Hash and store the user's password."""
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        """Verify a password against the stored hash."""
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """Get the user's full name, or email if name is not available."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.email
    
    def update_login_timestamp(self):
        """Update the last login timestamp."""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def set_up_bank_token(self, token):
        """
        Set the Up Bank API token.
        
        In a production environment, this would be encrypted.
        
        Args:
            token: The Up Bank personal access token
        """
        # TODO: Implement proper encryption for the token
        self.up_bank_token = token
        db.session.commit()
    
    def get_up_bank_token(self):
        """
        Get the Up Bank API token.
        
        In a production environment, this would be decrypted.
        
        Returns:
            The Up Bank personal access token
        """
        # TODO: Implement proper decryption for the token
        return self.up_bank_token
    
    def get_preference(self, key, default=None):
        """
        Get a user preference value.
        
        Args:
            key: The preference key
            default: Default value if preference is not set
            
        Returns:
            The preference value, or the default if not found
        """
        if not self.preferences:
            return default
            
        return self.preferences.get(key, default)
    
    def set_preference(self, key, value):
        """
        Set a user preference value.
        
        Args:
            key: The preference key
            value: The preference value
        """
        if not self.preferences:
            self.preferences = {}
            
        self.preferences[key] = value
        db.session.commit()
