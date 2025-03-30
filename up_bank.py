"""
Up Bank routes blueprint.

This module defines the routes for managing Up Bank integration,
including connecting accounts and viewing transactions.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app.services.bank_service import (
    connect_up_bank, sync_accounts, sync_transactions,
    get_transactions_by_week
)
from app.models import Account, AccountSource
from app.services.auth_service import check_token_rotation_needed

# Create the blueprint
up_bank_bp = Blueprint('up_bank', __name__)


@up_bank_bp.route('/')
@login_required
def view_upbank_dashboard():
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
                "type": account.type.value,
                "last_synced": account.last_synced.isoformat() if account.last_synced else None
            }
            for account in accounts
        ]
    })


@up_bank_bp.route('/connect', methods=['GET', 'POST'])
@login_required
def view_upbank_connect():
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
    
    # For GET requests, render the template
    return render_template('up_bank/connect.html')


@up_bank_bp.route('/sync', methods=['POST'])
@login_required
def action_upbank_sync():
    """Sync transactions from Up Bank."""
    # Get parameters from the form
    days_back = int(request.form.get('days_back', 30))
    
    # First sync accounts
    success_accounts, message_accounts, accounts_count = sync_accounts(current_user.id)
    
    if not success_accounts:
        flash(f'Failed to sync accounts: {message_accounts}', 'error')
        return redirect(url_for('up_bank.index'))
    
    # Then sync transactions
    success_tx, message_tx, tx_count = sync_transactions(current_user.id, days_back=days_back)
    
    if success_tx:
        flash(f'Successfully synced {accounts_count} accounts and {tx_count} transactions', 'success')
    else:
        flash(f'Successfully synced accounts but failed to sync transactions: {message_tx}', 'warning')
    
    return redirect(url_for('up_bank.index'))
    
    if not success_accounts:
        flash(f'Failed to sync accounts: {message_accounts}', 'error')
        return redirect(url_for('up_bank.index'))
    
    # Then sync transactions
    success_tx, message_tx, tx_count = sync_transactions(current_user.id, days_back=days_back)
    
    if success_tx:
        flash(f'Successfully synced {accounts_count} accounts and {tx_count} transactions', 'success')
    else:
        flash(f'Successfully synced accounts but failed to sync transactions: {message_tx}', 'warning')
    
    return redirect(url_for('up_bank.index'))


@up_bank_bp.route('/transactions')
@login_required
def api_upbank_transactions():
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


@up_bank_bp.route('/token-rotation-check')
@login_required
def api_upbank_token_status():
    """Check if the current user's token needs rotation."""
    # Get token rotation info
    rotation_info = check_token_rotation_needed(current_user)
    
    return jsonify(rotation_info)


@up_bank_bp.route('/disconnect', methods=['POST'])
@login_required
def action_upbank_disconnect():
    """Disconnect from Up Bank."""
    # Clear the user's Up Bank token
    current_user.set_up_bank_token(None)
    flash('Disconnected from Up Bank', 'success')
    return redirect(url_for('up_bank.index'))


@up_bank_bp.route('/accounts')
@login_required
def view_upbank_accounts():
    """View Up Bank accounts."""
    # Get user's Up Bank accounts
    accounts = Account.query.filter_by(
        user_id=current_user.id,
        source=AccountSource.UP_BANK
    ).order_by(Account.name).all()
    
    # Render the accounts template
    return render_template('up_bank/accounts.html', accounts=accounts)


@up_bank_bp.route('/accounts_detail/<int:account_id>')
@login_required
def view_upbank_account_detail(account_id):
    """View details for a specific account."""
    # Get the account
    account = Account.query.filter_by(
        id=account_id,
        user_id=current_user.id
    ).first_or_404()

    # Get balance history for visualization
    from app.models.account import AccountBalanceHistory

    # Get last 30 days of history
    today = datetime.utcnow().date()
    thirty_days_ago = today - timedelta(days=30)

    history = AccountBalanceHistory.query.filter(
        AccountBalanceHistory.account_id == account.id,
        AccountBalanceHistory.date >= thirty_days_ago
    ).order_by(AccountBalanceHistory.date).all()

    # Render the account detail template
    return render_template('up_bank/account_detail.html',
                           account=account, balance_history=history)


@up_bank_bp.route('/api/accounts')
@login_required
def api_upbank_accounts():
    """API endpoint for Up Bank accounts."""
    # Get user's Up Bank accounts
    accounts = Account.query.filter_by(
        user_id=current_user.id,
        source=AccountSource.UP_BANK
    ).order_by(Account.name).all()

    return jsonify({
        "accounts": [
            {
                "id": account.id,
                "name": account.name,
                "balance": float(account.balance),
                "currency": account.currency,
                "type": account.type.value,
                "last_synced": account.last_synced.isoformat()
                if account.last_synced else None,
                "external_id": account.external_id
            }
            for account in accounts
        ]
    })


@up_bank_bp.route('/api/account/<int:account_id>')
@login_required
def api_upbank_account_detail(account_id):
    """API endpoint for a specific account."""
    # Get the account
    account = Account.query.filter_by(
        id=account_id,
        user_id=current_user.id
    ).first_or_404()

    # Get balance history for visualization
    from app.models.account import AccountBalanceHistory

    # Get last 30 days of history
    today = datetime.utcnow().date()
    thirty_days_ago = today - timedelta(days=30)

    history = AccountBalanceHistory.query.filter(
        AccountBalanceHistory.account_id == account.id,
        AccountBalanceHistory.date >= thirty_days_ago
    ).order_by(AccountBalanceHistory.date).all()

    return jsonify({
        "account": {
            "id": account.id,
            "name": account.name,
            "balance": float(account.balance),
            "currency": account.currency,
            "type": account.type.value,
            "created_at": account.created_at.isoformat()
            if account.created_at else None,
            "updated_at": account.updated_at.isoformat()
            if account.updated_at else None,
            "last_synced": account.last_synced.isoformat()
            if account.last_synced else None,
            "external_id": account.external_id
        },
        "balance_history": [
            {
                "date": h.date.isoformat(),
                "balance": float(h.balance)
            }
            for h in history
        ]
    })
