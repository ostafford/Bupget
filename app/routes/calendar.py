"""
Calendar routes blueprint.

This module defines the routes for the calendar view,
which is the main interface for viewing and managing transactions.
"""

from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models import Transaction, WeeklySummary, RecurringExpense
from app.services.bank_service import get_transactions_by_week

# Create the blueprint
calendar_bp = Blueprint('calendar', __name__)


@calendar_bp.route('/')
@login_required
def index():
    """Calendar view page."""
    # For now, return a simple placeholder
    # In a real implementation, you would render a template
    return """
    <h1>Budget Calendar</h1>
    <div id="calendar-container">
        <p>Calendar view will be implemented here.</p>
    </div>
    <script src="/static/js/up-bank.js"></script>
    """


@calendar_bp.route('/api/weeks')
@login_required
def get_weeks():
    """Get transaction data for calendar weeks."""
    # Parse request parameters
    start_date_str = request.args.get('start')
    weeks = int(request.args.get('weeks', 4))
    
    # Parse start date or use current date
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str).date()
        except ValueError:
            start_date = datetime.now().date()
    else:
        start_date = datetime.now().date()
    
    # Find the Monday of the week containing the start date
    while start_date.weekday() != 0:  # 0 = Monday
        start_date -= timedelta(days=1)
    
    # Get transactions for the requested weeks
    transactions_by_week = get_transactions_by_week(current_user.id, start_date, weeks)
    
    # Format the response
    result = {}
    for week_start, transactions in transactions_by_week.items():
        # Get the weekly summary
        summary = WeeklySummary.query.filter_by(
            user_id=current_user.id,
            week_start_date=week_start
        ).first()
        
        # Format the week data
        week_data = {
            'start_date': week_start.isoformat(),
            'end_date': (week_start + timedelta(days=6)).isoformat(),
            'days': {},
            'summary': {
                'total_amount': float(summary.total_amount) if summary else 0,
                'total_expenses': float(summary.total_expenses) if summary else 0,
                'total_income': float(summary.total_income) if summary else 0,
                'total_extras': float(summary.total_extras) if summary else 0
            }
        }
        
        # Group transactions by day
        for tx in transactions:
            day_str = tx.date.isoformat()
            if day_str not in week_data['days']:
                week_data['days'][day_str] = []
            
            week_data['days'][day_str].append({
                'id': tx.id,
                'description': tx.description,
                'amount': float(tx.amount),
                'is_extra': tx.is_extra,
                'category_id': tx.category_id,
                'source': tx.source.value
            })
        
        result[week_start.isoformat()] = week_data
    
    return jsonify(result)


@calendar_bp.route('/api/recurring')
@login_required
def get_recurring_expenses():
    """Get recurring expenses for the calendar."""
    # Get all active recurring expenses for the current user
    expenses = RecurringExpense.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    
    # Format the response
    result = []
    for expense in expenses:
        result.append({
            'id': expense.id,
            'name': expense.name,
            'amount': float(expense.amount),
            'frequency': expense.frequency.value,
            'next_date': expense.next_date.isoformat() if expense.next_date else None
        })
    
    return jsonify(result)


@calendar_bp.route('/api/transaction/<int:transaction_id>', methods=['GET'])
@login_required
def get_transaction(transaction_id):
    """Get details for a specific transaction."""
    # Find the transaction
    transaction = Transaction.query.filter_by(
        id=transaction_id,
        user_id=current_user.id
    ).first()
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    # Format the response
    result = {
        'id': transaction.id,
        'date': transaction.date.isoformat(),
        'description': transaction.description,
        'amount': float(transaction.amount),
        'is_extra': transaction.is_extra,
        'category_id': transaction.category_id,
        'source': transaction.source.value,
        'notes': transaction.notes,
        'created_at': transaction.created_at.isoformat(),
        'updated_at': transaction.updated_at.isoformat()
    }
    
    return jsonify(result)


@calendar_bp.route('/api/transaction', methods=['POST'])
@login_required
def create_transaction():
    """Create a new transaction."""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['date', 'amount', 'description']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Parse date
    try:
        date = datetime.fromisoformat(data['date']).date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    # Create transaction
    transaction = Transaction(
        date=date,
        amount=float(data['amount']),
        description=data['description'],
        is_extra=data.get('is_extra', False),
        category_id=data.get('category_id'),
        notes=data.get('notes'),
        source=data.get('source', 'MANUAL'),
        user_id=current_user.id,
        account_id=data.get('account_id')
    )
    
    try:
        from app.extensions import db
        db.session.add(transaction)
        db.session.commit()
        
        # Update weekly summary
        WeeklySummary.calculate_for_week(current_user.id, transaction.week_start_date)
        
        return jsonify({
            'success': True,
            'transaction': {
                'id': transaction.id,
                'date': transaction.date.isoformat(),
                'description': transaction.description,
                'amount': float(transaction.amount)
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/transaction/<int:transaction_id>', methods=['PUT'])
@login_required
def update_transaction(transaction_id):
    """Update an existing transaction."""
    # Find the transaction
    transaction = Transaction.query.filter_by(
        id=transaction_id,
        user_id=current_user.id
    ).first()
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    # Get update data
    data = request.get_json()
    
    # Update fields
    if 'date' in data:
        try:
            transaction.date = datetime.fromisoformat(data['date']).date()
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    
    if 'amount' in data:
        transaction.amount = float(data['amount'])
    
    if 'description' in data:
        transaction.description = data['description']
    
    if 'is_extra' in data:
        transaction.is_extra = bool(data['is_extra'])
    
    if 'category_id' in data:
        transaction.category_id = data['category_id']
    
    if 'notes' in data:
        transaction.notes = data['notes']
    
    try:
        from app.extensions import db
        transaction.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Update weekly summary
        WeeklySummary.calculate_for_week(current_user.id, transaction.week_start_date)
        
        return jsonify({
            'success': True,
            'transaction': {
                'id': transaction.id,
                'date': transaction.date.isoformat(),
                'description': transaction.description,
                'amount': float(transaction.amount)
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/api/transaction/<int:transaction_id>', methods=['DELETE'])
@login_required
def delete_transaction(transaction_id):
    """Delete a transaction."""
    # Find the transaction
    transaction = Transaction.query.filter_by(
        id=transaction_id,
        user_id=current_user.id
    ).first()
    
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404
    
    try:
        from app.extensions import db
        # Remember the week start date before deleting
        week_start_date = transaction.week_start_date
        
        # Delete the transaction
        db.session.delete(transaction)
        db.session.commit()
        
        # Update weekly summary
        WeeklySummary.calculate_for_week(current_user.id, week_start_date)
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
