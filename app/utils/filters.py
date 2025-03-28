"""
Template filters.

This module defines Jinja2 template filters for formatting data.
"""

from datetime import datetime


def format_currency(value, currency='AUD'):
    """
    Format a value as currency.
    
    Args:
        value: The value to format
        currency: The currency code (default: AUD)
    
    Returns:
        str: Formatted currency string
    """
    try:
        # Format as currency with 2 decimal places
        value = float(value)
        if currency == 'AUD':
            return f'${value:,.2f}'
        else:
            return f'{value:,.2f} {currency}'
    except (ValueError, TypeError):
        return value


def format_datetime(value, format='%d-%m-%Y %H:%M'):
    """
    Format a datetime object.
    
    Args:
        value: The datetime to format
        format: The format string (default: %d-%m-%Y %H:%M)
    
    Returns:
        str: Formatted datetime string
    """
    if not value:
        return ''
    
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return value
    
    try:
        return value.strftime(format)
    except (ValueError, TypeError, AttributeError):
        return value


def register_template_filters(app):
    """
    Register template filters with the Flask application.
    
    Args:
        app: The Flask application
    """
    app.template_filter('format_currency')(format_currency)
    app.template_filter('format_datetime')(format_datetime)
