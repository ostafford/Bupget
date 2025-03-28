"""
Simplified forecast models.

This is a temporary simplified version to avoid circular dependencies.
We'll replace this with the full implementation in a later phase.
"""

from datetime import datetime, date
from app.extensions import db


class TargetDateForecast(db.Model):
    """
    Simplified model for target date forecasts.
    """
    __tablename__ = 'target_date_forecasts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    target_date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    projected_balance = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_calculated = db.Column(db.DateTime, default=datetime.utcnow)


class MonthlyForecast(db.Model):
    """
    Simplified model for monthly forecasts.
    """
    __tablename__ = 'monthly_forecasts'
    
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    projected_balance = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
