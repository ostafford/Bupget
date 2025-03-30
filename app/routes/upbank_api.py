"""
Up Bank API Routes Blueprint.

This module defines API routes for Up Bank integration that return JSON data.
These endpoints are used by frontend JavaScript to fetch data without page reloads,
as well as by other systems that need programmatic access to Up Bank data.

These routes are separate from the view routes to maintain clear separation
between HTML views and JSON API endpoints.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from app.models import Account, AccountSource, AccountBalanceHistory
from app.services.bank_service import sync_accounts, sync_transactions, get_transactions_by_week
from app.services.auth_service import check_token_rotation_needed

# Create the blueprint for API endpoints
upbank_api_bp = Blueprint('upbank_api', __name__, url_prefix='/api/up-bank')


@upbank_api_bp.route('/status')
@login_required
def api_upbank_status():
    """
    Get Up Bank connection status for the current user.
    
    This endpoint returns information about whether the user
    is connected to Up Bank and the status of their token.
    
    Returns:
        JSON response with connection status details
    """
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


@upbank_api_bp.route('/token-check')
@login_required
def api_upbank_token_status():
    """
    Check if the current user's token needs rotation.
    
    This endpoint checks if the user's Up Bank token is old
    and should be rotated for security reasons.
    
    Returns:
        JSON response with token rotation status
    """
    # Get token rotation info
    rotation_info = check_token_rotation_needed(current_user)
    
    return jsonify(rotation_info)


@upbank_api_bp.route('/accounts')
@login_required
def api_upbank_accounts():
    """
    Get all Up Bank accounts for the current user.
    
    This endpoint returns all the user's Up Bank accounts,
    including their balances and other details.
    
    Returns:
        JSON response with accounts data
    """
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


@upbank_api_bp.route('/accounts/<int:account_id>')
@login_required
def api_upbank_account_detail(account_id):
    """
    Get detailed information for a specific Up Bank account.
    
    This endpoint returns detailed information about a single account,
    including its balance history and other details.
    
    Args:
        account_id (int): The ID of the account to retrieve
        
    Returns:
        JSON response with account details and balance history
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


@upbank_api_bp.route('/transactions')
@login_required
def api_upbank_transactions():
    """
    Get transactions from Up Bank grouped by week.
    
    This endpoint returns the user's transactions organized by week,
    which is useful for calendar-based views.
    
    Query Parameters:
        weeks (int): Number of weeks of history to retrieve (default: 4)
        
    Returns:
        JSON response with transactions grouped by week
    """
    # Get request parameters
    weeks = int(request.args.get('weeks', 4))
    
    # Get transactions grouped by week
    transactions_by_week = get_transactions_by_week(current_user.id, weeks=weeks)
    
    # Format the response
    result = {}
    for week_start, transactions in transactions_by_week.items():
        result[week_start.isoformat()] = [
            {
                "id": tx.id,
                "date": tx.date.isoformat(),
                "description": tx.description,
                "amount": float(tx.amount),
                "category_id": tx.category_id,
                "is_extra": tx.is_extra
            }
            for tx in transactions
        ]
    
    return jsonify(result)


@upbank_api_bp.route('/sync', methods=['POST'])
@login_required
def api_upbank_sync():
    """
    Trigger synchronization of Up Bank data.
    
    This endpoint allows triggering the synchronization of accounts
    and transactions from Up Bank via an API call.
    
    Request Body:
        days_back (int): Number of days of history to sync (default: 30)
        
    Returns:
        JSON response with synchronization results
    """
    # Get parameters from JSON body
    data = request.get_json() or {}
    days_back = data.get('days_back', 30)
    
    # First sync accounts
    success_accounts, message_accounts, accounts_count = sync_accounts(current_user.id)
    
    if not success_accounts:
        return jsonify({
            "success": False,
            "message": f"Failed to sync accounts: {message_accounts}"
        }), 500
    
    # Then sync transactions
    success_tx, message_tx, tx_count = sync_transactions(current_user.id, days_back=days_back)
    
    if success_tx:
        return jsonify({
            "success": True,
            "message": f"Successfully synced {accounts_count} accounts and {tx_count} transactions",
            "accounts_count": accounts_count,
            "transaction_count": tx_count
        })
    else:
        return jsonify({
            "success": False,
            "message": f"Successfully synced accounts but failed to sync transactions: {message_tx}"
        }), 500
