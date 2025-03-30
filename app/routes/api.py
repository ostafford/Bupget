"""
API routes blueprint.

This module defines the API routes for the application,
which provide integration with external services like Up Bank.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.services.bank_service import connect_up_bank, sync_accounts, sync_transactions
from app.services.auth_service import validate_up_bank_token, store_up_bank_token, get_up_bank_connection_status

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
    from app.api.webhooks import verify_webhook_signature, process_webhook
    
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
