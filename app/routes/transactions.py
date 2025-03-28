"""
Transaction routes blueprint.

This module defines the routes for managing transactions,
including viewing, adding, editing, and deleting transactions.
"""

from flask import Blueprint, render_template, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from app.models import Transaction, Account

# Create the blueprint
transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('/')
@login_required
def index():
    """Transaction list route."""
    return "Transaction list page (to be implemented)"


@transactions_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add transaction route."""
    return "Add transaction page (to be implemented)"


@transactions_bp.route('/edit/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit(transaction_id):
    """Edit transaction route."""
    return f"Edit transaction page for ID {transaction_id} (to be implemented)"


@transactions_bp.route('/delete/<int:transaction_id>', methods=['POST'])
@login_required
def delete(transaction_id):
    """Delete transaction route."""
    return f"Delete transaction with ID {transaction_id} (to be implemented)"


@transactions_bp.route('/api/account/<int:account_id>')
@login_required
def api_account_transactions(account_id):
    """API endpoint for account transactions."""
    # Get the account
    account = Account.query.filter_by(
        id=account_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Get transactions for the account
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    
    transactions = Transaction.query.filter_by(
        account_id=account.id,
        user_id=current_user.id
    ).order_by(Transaction.date.desc(), Transaction.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        "account_id": account.id,
        "account_name": account.name,
        "page": page,
        "per_page": per_page,
        "total": transactions.total,
        "pages": transactions.pages,
        "has_next": transactions.has_next,
        "has_prev": transactions.has_prev,
        "transactions": [
            {
                "id": tx.id,
                "date": tx.date.isoformat(),
                "description": tx.description,
                "amount": float(tx.amount),
                "is_extra": tx.is_extra,
                "category_id": tx.category_id,
                "source": tx.source.value
            }
            for tx in transactions.items
        ]
    })
