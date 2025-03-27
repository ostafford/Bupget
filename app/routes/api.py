"""
API routes blueprint.

This module defines the API routes for the application,
which provide integration with external services like Up Bank.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.services.bank_service import connect_up_bank, sync_accounts, sync_transactions

# Create the blueprint
api_bp = Blueprint('api', __name__)


@api_bp.route('/up-bank/connect', methods=['POST'])
@login_required
def connect_up_bank_route():
    """Connect to Up Bank API route."""
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


@api_bp.route('/up-bank/sync', methods=['POST'])
@login_required
def sync_up_bank_route():
    """Sync transactions from Up Bank route."""
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


@api_bp.route('/up-bank/webhook', methods=['POST'])
def up_bank_webhook_route():
    """Webhook endpoint for Up Bank real-time updates."""
    # Get the webhook data
    data = request.get_json()
    
    # Verify webhook signature (if implemented by Up Bank)
    # TODO: Implement webhook signature verification
    
    # Process the webhook
    # TODO: Implement webhook processing based on event type
    
    # For now, just log the webhook
    current_app.logger.info(f"Received Up Bank webhook: {data}")
    
    return jsonify({
        "success": True,
        "message": "Webhook received"
    })
