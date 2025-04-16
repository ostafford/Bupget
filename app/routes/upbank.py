"""
Up Bank integration routes.

This module provides routes for Up Bank integration, including
both HTML views for user interaction and API endpoints for data exchange.
"""

import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from app.models import User, Account, AccountSource, AccountBalanceHistory
from app.services.bank_service import connect_up_bank, sync_accounts, sync_transactions
from app.services.auth_service import validate_up_bank_token, store_up_bank_token, get_up_bank_connection_status, check_token_rotation_needed
from app.api.up_bank import get_up_bank_api
from app.api.webhooks import verify_webhook_signature, process_webhook

# Configure logging
logger = logging.getLogger(__name__)

# Create the blueprint with a general URL prefix
upbank_bp = Blueprint('upbank', __name__, url_prefix='/up-bank')

#
# HTML View Routes
#

@upbank_bp.route('/')
@login_required
def index():
    """Up Bank dashboard page."""
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


@upbank_bp.route('/connect', methods=['GET', 'POST'])
@login_required
def connect():
    """
    Handle Up Bank connection.
    
    GET: Display connection form
    POST: Process connection request
    """
    if request.method == 'POST':
        # Get the token from the form
        token = request.form.get('token')
        
        if not token:
            flash('Token is required', 'error')
            return redirect(url_for('upbank.connect'))
        
        # Connect to Up Bank
        success = connect_up_bank(current_user.id, token)
        
        if success:
            flash('Successfully connected to Up Bank', 'success')
            return redirect(url_for('upbank.index'))
        else:
            flash('Failed to connect to Up Bank', 'error')
    
    # For GET requests, render the template
    return render_template('up_bank/connect.html')


@upbank_bp.route('/accounts')
@login_required
def accounts():
    """Display list of Up Bank accounts."""
    # Get user's Up Bank accounts
    accounts = Account.query.filter_by(
        user_id=current_user.id,
        source=AccountSource.UP_BANK
    ).order_by(Account.name).all()
    
    # Render the accounts template
    return render_template('up_bank/accounts.html', accounts=accounts)


@upbank_bp.route('/accounts/<int:account_id>')
@login_required
def account_detail(account_id):
    """
    Display detailed account information.
    
    Args:
        account_id (int): The account ID
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


@upbank_bp.route('/sync', methods=['POST'])
@login_required
def sync():
    """Sync data from Up Bank."""
    # Get parameters from the form
    days_back = int(request.form.get('days_back', 30))
    
    # First sync accounts
    success_accounts, message_accounts, accounts_count = sync_accounts(current_user.id)
    
    if not success_accounts:
        flash(f'Failed to sync accounts: {message_accounts}', 'error')
        return redirect(url_for('upbank.index'))
    
    # Then sync transactions
    success_tx, message_tx, tx_count = sync_transactions(current_user.id, days_back=days_back)
    
    if success_tx:
        flash(f'Successfully synced {accounts_count} accounts and {tx_count} transactions', 'success')
    else:
        flash(f'Successfully synced accounts but failed to sync transactions: {message_tx}', 'warning')
    
    return redirect(url_for('upbank.index'))


@upbank_bp.route('/disconnect', methods=['POST'])
@login_required
def disconnect():
    """Disconnect from Up Bank."""
    # Clear the user's Up Bank token
    current_user.set_up_bank_token(None)
    flash('Disconnected from Up Bank', 'success')
    return redirect(url_for('upbank.index'))


#
# API Routes
#

@upbank_bp.route('/api/connect', methods=['POST'])
@login_required
def api_connect():
    """API endpoint to connect to Up Bank."""
    # Get the token from the request
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({
            "success": False,
            "message": "Token is required"
        }), 400
    
    # Connect to Up Bank
    success = connect_up_bank(current_user.id, token)
    
    if success:
        return jsonify({
            "success": True,
            "message": "Successfully connected to Up Bank"
        })
    else:
        return jsonify({
            "success": False,
            "message": "Failed to connect to Up Bank"
        }), 500


@upbank_bp.route('/api/sync', methods=['POST'])
@login_required
def api_sync():
    """API endpoint to sync data from Up Bank."""
    # Get parameters from the request
    data = request.get_json() or {}
    days_back = data.get('days_back', 30)
    
    # First sync accounts
    success, message, _ = sync_accounts(current_user.id)
    
    if not success:
        return jsonify({
            "success": False,
            "message": f"Failed to sync accounts: {message}"
        }), 500
    
    # Then sync transactions
    success, message, tx_count = sync_transactions(current_user.id, days_back=days_back)
    
    if success:
        return jsonify({
            "success": True,
            "message": message,
            "transaction_count": tx_count
        })
    else:
        return jsonify({
            "success": False,
            "message": message
        }), 500


@upbank_bp.route('/api/status')
@login_required
def api_status():
    """API endpoint to get Up Bank connection status."""
    # Check if user has an Up Bank token
    has_token = current_user.get_up_bank_token() is not None
    
    # Get user's Up Bank accounts
    accounts = Account.query.filter_by(
        user_id=current_user.id,
        source=AccountSource.UP_BANK
    ).all()
    
    return jsonify({
        "connected": has_token,
        "accounts_count": len(accounts),
        "last_sync": max([account.last_synced for account in accounts]) if accounts else None
    })


@upbank_bp.route('/api/token-check')
@login_required
def api_token_check():
    """API endpoint to check token rotation status."""
    # Get token rotation info
    rotation_info = check_token_rotation_needed(current_user)
    
    return jsonify(rotation_info)


@upbank_bp.route('/api/accounts')
@login_required
def api_accounts():
    """API endpoint to get Up Bank accounts."""
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
                "last_synced": account.last_synced.isoformat() if account.last_synced else None,
                "external_id": account.external_id
            }
            for account in accounts
        ]
    })


@upbank_bp.route('/api/accounts/<int:account_id>')
@login_required
def api_account_detail(account_id):
    """API endpoint to get detailed account information."""
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
    
    return jsonify({
        "account": {
            "id": account.id,
            "name": account.name,
            "balance": float(account.balance),
            "currency": account.currency,
            "type": account.type.value,
            "created_at": account.created_at.isoformat() if account.created_at else None,
            "updated_at": account.updated_at.isoformat() if account.updated_at else None,
            "last_synced": account.last_synced.isoformat() if account.last_synced else None,
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


@upbank_bp.route('/api/webhook', methods=['POST'])
def api_webhook():
    """API endpoint for Up Bank webhooks."""
    # Get the webhook data
    data = request.get_json()
    
    # Get the webhook signature from header
    signature = request.headers.get('X-Up-Authenticity-Signature')
    
    # Get the webhook secret from config
    webhook_secret = current_app.config.get('UP_BANK_WEBHOOK_SECRET')
    
    # For security, get the raw request data for signature verification
    request_data = request.get_data()
    
    # Log webhook receipt
    current_app.logger.info("Received Up Bank webhook")
    
    # Verify webhook signature if configured
    if webhook_secret:
        if not signature:
            current_app.logger.warning("Webhook signature missing")
            return jsonify({
                "success": False,
                "message": "Webhook signature missing"
            }), 401
            
        if not verify_webhook_signature(request_data, signature, webhook_secret):
            current_app.logger.warning("Invalid webhook signature")
            return jsonify({
                "success": False,
                "message": "Invalid webhook signature"
            }), 401
    else:
        current_app.logger.warning("Webhook secret not configured, skipping signature verification")
    
    # Process the webhook
    result = process_webhook(data)
    
    if result["success"]:
        current_app.logger.info(f"Webhook processed successfully: {result['message']}")
        return jsonify({
            "success": True,
            "message": result["message"]
        })
    else:
        current_app.logger.error(f"Webhook processing failed: {result['message']}")
        return jsonify({
            "success": False,
            "message": result["message"]
        }), 500


@upbank_bp.route('/api/validate-token', methods=['POST'])
@login_required
def api_validate_token():
    """API endpoint to validate an Up Bank token."""
    # Get the token from the request
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return jsonify({
            "success": False,
            "message": "Token is required"
        }), 400
    
    # Validate the token
    validation = validate_up_bank_token(token)
    
    return jsonify(validation)