"""
API routes blueprint.

This module defines the API routes for the application,
which provide integration with external services like Up Bank.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required

# Create the blueprint
api_bp = Blueprint('api', __name__)


@api_bp.route('/up-bank/connect', methods=['POST'])
@login_required
def connect_up_bank():
    """Connect to Up Bank API route."""
    return jsonify({"message": "Up Bank connection endpoint (to be implemented)"})


@api_bp.route('/up-bank/sync', methods=['POST'])
@login_required
def sync_up_bank():
    """Sync transactions from Up Bank route."""
    return jsonify({"message": "Up Bank sync endpoint (to be implemented)"})


@api_bp.route('/up-bank/webhook', methods=['POST'])
def up_bank_webhook():
    """Webhook endpoint for Up Bank real-time updates."""
    return jsonify({"message": "Up Bank webhook received (to be implemented)"})
