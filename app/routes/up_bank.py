"""
Up Bank routes blueprint.

This module defines the routes for managing Up Bank integration,
including connecting accounts and viewing transactions.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.services.bank_service import (
    connect_up_bank, sync_accounts, sync_transactions,
    get_transactions_by_week
)
from app.models import Account, AccountSource

# Create the blueprint
up_bank_bp = Blueprint('up_bank', __name__)


@up_bank_bp.route('/')
@login_required
def index():
    """Up Bank integration overview page."""
    # Check if user has an Up Bank token
    has_token = current_user.get_up_bank_token() is not None
    
    # Get user's Up Bank accounts
    accounts = Account.query.filter_by(
        user_id=current_user.id,
        source=AccountSource.UP_BANK
    ).all()
    
    # For now, render a simple response
    # In a real implementation, you would render a template
    return jsonify({
        "connected": has_token,
        "accounts_count": len(accounts),
        "accounts": [
            {
                "id": account.id,
                "name": account.name,
                "balance": float(account.balance),
                "type": account.type.value
            }
            for account in accounts
        ]
    })


@up_bank_bp.route('/connect', methods=['GET', 'POST'])
@login_required
def connect():
    """Connect to Up Bank API page."""
    if request.method == 'POST':
        # Get the token from the form
        token = request.form.get('token')
        
        if not token:
            flash('Token is required', 'error')
            return redirect(url_for('up_bank.connect'))
        
        # Connect to Up Bank
        success = connect_up_bank(current_user.id, token)
        
        if success:
            flash('Successfully connected to Up Bank', 'success')
            return redirect(url_for('up_bank.index'))
        else:
            flash('Failed to connect to Up Bank', 'error')
    
    # For now, render a simple form
    # In a real implementation, you would render a template
    return """
    <h1>Connect to Up Bank</h1>
    <p>Enter your Up Bank Personal Access Token to connect your account.</p>
    <form method="post">
        <input type="text" name="token" placeholder="Personal Access Token" required>
        <button type="submit">Connect</button>
    </form>
    """


@up_bank_bp.route('/sync', methods=['POST'])
@login_required
def sync():
    """Sync transactions from Up Bank."""
    # Get parameters from the form
    days_back = int(request.form.get('days_back', 30))
    
    # First sync accounts
    success_accounts, message_accounts, _ = sync_accounts(current_user.id)
    
    if not success_accounts:
        flash(f'Failed to sync accounts: {message_accounts}', 'error')
        return redirect(url_for('up_bank.index'))
    
    # Then sync transactions
    success_tx, message_tx, tx_count = sync_transactions(current_user.id, days_back=days_back)
    
    if success_tx:
        flash(f'Successfully synced {tx_count} transactions: {message_tx}', 'success')
    else:
        flash(f'Failed to sync transactions: {message_tx}', 'error')
    
    return redirect(url_for('up_bank.index'))


@up_bank_bp.route('/transactions')
@login_required
def transactions():
    """View Up Bank transactions."""
    # Get transactions grouped by week
    transactions_by_week = get_transactions_by_week(current_user.id, weeks=4)
    
    # For now, render a simple JSON response
    # In a real implementation, you would render a template
    result = {}
    for week_start, transactions in transactions_by_week.items():
        result[week_start.isoformat()] = [
            {
                "id": tx.id,
                "date": tx.date.isoformat(),
                "description": tx.description,
                "amount": float(tx.amount)
            }
            for tx in transactions
        ]
    
    return jsonify(result)


@up_bank_bp.route('/disconnect', methods=['POST'])
@login_required
def disconnect():
    """Disconnect from Up Bank."""
    # Clear the user's Up Bank token
    current_user.set_up_bank_token(None)
    flash('Disconnected from Up Bank', 'success')
    return redirect(url_for('up_bank.index'))
