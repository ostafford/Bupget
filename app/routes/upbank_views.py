"""
Up Bank View Routes Blueprint.

This module defines the routes that render HTML templates for Up Bank integration,
including connecting accounts, viewing account lists, and account details.

These routes are separate from the API routes to maintain clear separation
between HTML views and JSON API endpoints.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from app.models import Account, AccountSource, AccountBalanceHistory
from app.services.bank_service import connect_up_bank, sync_accounts, sync_transactions

# Create the blueprint for HTML views
upbank_view_bp = Blueprint('up_bank', __name__, url_prefix='/up-bank')


@upbank_view_bp.route('/')
@login_required
def index():
    """Up Bank dashboard page (alias for view_upbank_dashboard)."""
    return view_upbank_dashboard()


@upbank_view_bp.route('/dashboard')
@login_required
def view_upbank_dashboard():
    """
    Render the Up Bank dashboard view.
    
    This view displays an overview of the user's Up Bank connection status
    and their accounts. It serves as the main entry point for Up Bank
    integration.
    
    Returns:
        The rendered dashboard template with connection status and accounts
    """
    # Check if user has an Up Bank token
    has_token = current_user.get_up_bank_token() is not None
    
    # Get user's Up Bank accounts
    accounts = Account.query.filter_by(
        user_id=current_user.id,
        source=AccountSource.UP_BANK
    ).all()
    
    # Render the dashboard template
    return render_template(
        'up_bank/dashboard.html',
        connected=has_token,
        accounts=accounts,
        accounts_count=len(accounts)
    )


@upbank_view_bp.route('/connect', methods=['GET', 'POST'])
@login_required
def view_upbank_connect():
    """
    Render the Up Bank connection page and handle connection requests.
    
    GET: Displays a form to enter an Up Bank API token
    POST: Processes the token and attempts to connect to Up Bank
    
    Returns:
        GET: The rendered connection form template
        POST: Redirect to dashboard on success, or back to form on failure
    """
    if request.method == 'POST':
        # Get the token from the form
        token = request.form.get('token')
        
        if not token:
            flash('Token is required', 'error')
            return redirect(url_for('upbank_view.view_upbank_connect'))
        
        # Connect to Up Bank
        success = connect_up_bank(current_user.id, token)
        
        if success:
            flash('Successfully connected to Up Bank', 'success')
            return redirect(url_for('upbank_view.view_upbank_dashboard'))
        else:
            flash('Failed to connect to Up Bank', 'error')
    
    # For GET requests, render the template
    return render_template('up_bank/connect.html')


@upbank_view_bp.route('/accounts')
@login_required
def view_upbank_accounts():
    """
    Render the Up Bank accounts list view.
    
    This view displays all accounts the user has in Up Bank,
    including their names, types, and current balances.
    
    Returns:
        The rendered accounts template with the list of accounts
    """
    # Get user's Up Bank accounts
    accounts = Account.query.filter_by(
        user_id=current_user.id,
        source=AccountSource.UP_BANK
    ).order_by(Account.name).all()
    
    # Render the accounts template
    return render_template('up_bank/accounts.html', accounts=accounts)


@upbank_view_bp.route('/accounts/<int:account_id>')
@login_required
def view_upbank_account_detail(account_id):
    """
    Render the detailed view for a specific Up Bank account.
    
    This view displays detailed information about a single account,
    including its balance history and recent transactions.
    
    Args:
        account_id (int): The ID of the account to display
        
    Returns:
        The rendered account detail template with account data and history
    """
    # Get the account
    account = Account.query.filter_by(
        id=account_id,
        user_id=current_user.id
    ).first_or_404()
    
    # Get last 30 days of balance history
    today = datetime.utcnow().date()
    thirty_days_ago = today - timedelta(days=30)
    
    history = AccountBalanceHistory.query.filter(
        AccountBalanceHistory.account_id == account.id,
        AccountBalanceHistory.date >= thirty_days_ago
    ).order_by(AccountBalanceHistory.date).all()
    
    # Render the account detail template
    return render_template('up_bank/account_detail.html', account=account, balance_history=history)


@upbank_view_bp.route('/sync', methods=['POST'])
@login_required
def action_upbank_sync():
    """
    Handle account and transaction synchronization requests.
    
    This action endpoint triggers the synchronization of accounts and
    transactions from Up Bank to the local database.
    
    Returns:
        Redirect to the dashboard with a status message
    """
    # Get parameters from the form
    days_back = int(request.form.get('days_back', 30))
    
    # First sync accounts
    success_accounts, message_accounts, accounts_count = sync_accounts(current_user.id)
    
    if not success_accounts:
        flash(f'Failed to sync accounts: {message_accounts}', 'error')
        return redirect(url_for('upbank_view.view_upbank_dashboard'))
    
    # Then sync transactions
    success_tx, message_tx, tx_count = sync_transactions(current_user.id, days_back=days_back)
    
    if success_tx:
        flash(f'Successfully synced {accounts_count} accounts and {tx_count} transactions', 'success')
    else:
        flash(f'Successfully synced accounts but failed to sync transactions: {message_tx}', 'warning')
    
    return redirect(url_for('upbank_view.view_upbank_dashboard'))


@upbank_view_bp.route('/disconnect', methods=['POST'])
@login_required
def action_upbank_disconnect():
    """
    Handle account disconnection requests.
    
    This action endpoint disconnects the user from Up Bank by
    clearing their stored API token.
    
    Returns:
        Redirect to the dashboard with a status message
    """
    # Clear the user's Up Bank token
    current_user.set_up_bank_token(None)
    flash('Disconnected from Up Bank', 'success')
    return redirect(url_for('upbank_view.view_upbank_dashboard'))
