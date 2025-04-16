"""
Up Bank webhook handling.

This module processes webhooks from Up Bank for real-time updates.
"""

import hmac
import hashlib
import json
import logging
from datetime import datetime
from flask import current_app, request
from app.extensions import db
from app.models import User, Transaction, Account
from app.api.up_bank import get_up_bank_api, UpBankError
from app.api.error_handling import retry, handle_api_exception, APIErrorResponse

# Configure logging
logger = logging.getLogger(__name__)


def verify_webhook_signature(request_data, signature, webhook_secret):
    """
    Verify the webhook signature from Up Bank.
    
    Args:
        request_data (bytes): The raw request body
        signature (str): The provided signature
        webhook_secret (str): The webhook secret
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not webhook_secret or not signature:
        logger.warning("Cannot verify webhook: missing secret or signature")
        return False
    
    try:
        # Create a signature using HMAC with SHA256
        computed_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            request_data,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures using constant-time comparison
        return hmac.compare_digest(computed_signature, signature)
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {str(e)}")
        return False


def process_webhook(data, user_id=None):
    """
    Process a webhook payload from Up Bank.
    
    Args:
        data (dict): The webhook payload
        user_id (int, optional): Specific user ID to use, or None to find by account
        
    Returns:
        dict: Processing result with status and details
    """
    try:
        # Extract event type
        event_type = data.get('data', {}).get('attributes', {}).get('eventType')
        
        if not event_type:
            error_msg = "Invalid webhook payload: missing eventType"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        
        logger.info(f"Processing webhook with event type: {event_type}")
        
        # Handle different event types
        if event_type == 'TRANSACTION_CREATED':
            return process_transaction_created(data, user_id)
        elif event_type == 'TRANSACTION_SETTLED':
            return process_transaction_settled(data, user_id)
        elif event_type == 'TRANSACTION_DELETED':
            return process_transaction_deleted(data, user_id)
        else:
            logger.info(f"Ignoring unsupported event type: {event_type}")
            return {"success": True, "message": f"Ignoring unsupported event type: {event_type}"}
            
    except Exception as e:
        error = handle_api_exception(e, "Webhook Processing", "process_webhook")
        logger.error(f"Error processing webhook: {error.message}")
        return {"success": False, "message": error.message}


@retry(exceptions=[Exception], tries=3, delay=1, backoff=2, jitter=0.1)
def process_transaction_created(data, user_id=None):
    """
    Process a TRANSACTION_CREATED webhook.
    
    Args:
        data (dict): The webhook payload
        user_id (int, optional): Specific user ID to use, or None to find by account
        
    Returns:
        dict: Processing result
    """
    # Extract transaction data
    try:
        transaction_data = data.get('data', {}).get('relationships', {}).get('transaction', {}).get('data', {})
        if not transaction_data or 'id' not in transaction_data:
            error_msg = "Missing transaction data in webhook"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        
        transaction_id = transaction_data['id']
        logger.info(f"Processing transaction created event for transaction ID: {transaction_id}")
        
        # Find the user by account if not specified
        if not user_id:
            account_data = data.get('data', {}).get('relationships', {}).get('account', {}).get('data', {})
            if not account_data or 'id' not in account_data:
                error_msg = "Missing account data in webhook"
                logger.error(error_msg)
                return {"success": False, "message": error_msg}
            
            account_id = account_data['id']
            account = Account.query.filter_by(external_id=account_id).first()
            
            if not account:
                error_msg = f"Account not found: {account_id}"
                logger.error(error_msg)
                return {"success": False, "message": error_msg}
            
            user_id = account.user_id
        
        # Get the user
        user = User.query.get(user_id)
        if not user:
            error_msg = f"User not found: {user_id}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        
        # Get the Up Bank token for this user
        token = user.get_up_bank_token()
        if not token:
            error_msg = f"Up Bank token not found for user: {user_id}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        
        # Get the Up Bank API
        api = get_up_bank_api(token=token)
        
        # Get the transaction from Up Bank
        transaction = api.get_transaction_by_id(transaction_id)
        if not transaction:
            error_msg = f"Failed to retrieve transaction: {transaction_id}"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        
        # Process the transaction (similar to sync logic)
        result = process_up_bank_transaction(transaction, user_id)
        
        if result:
            logger.info(f"Successfully processed transaction created: {transaction_id}")
            return {"success": True, "message": "Transaction created", "transaction_id": transaction_id}
        else:
            error_msg = "Failed to process transaction"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
            
    except UpBankError as e:
        # Handle Up Bank API errors
        error = handle_api_exception(e, "Up Bank API", "process_transaction_created")
        logger.error(f"Up Bank API error: {error.message}")
        
        # Determine if we should retry
        if hasattr(e, 'status_code') and e.status_code == 429:
            # Rate limited, should retry
            logger.warning(f"Rate limited, retrying after delay: {getattr(e, 'retry_after', 1)} seconds")
            raise  # Raise for retry mechanism
        elif hasattr(e, 'status_code') and e.status_code >= 500:
            # Server error, should retry
            logger.warning("Server error, retrying")
            raise  # Raise for retry mechanism
        else:
            # Other API error, don't retry
            return {"success": False, "message": error.message}
            
    except Exception as e:
        error = handle_api_exception(e, "Webhook Processing", "process_transaction_created")
        logger.error(f"Error processing transaction created: {error.message}")
        
        # For general exceptions, we'll retry
        raise  # Raise for retry mechanism


@retry(exceptions=[Exception], tries=3, delay=1, backoff=2, jitter=0.1)
def process_transaction_settled(data, user_id=None):
    """
    Process a TRANSACTION_SETTLED webhook.
    
    Args:
        data (dict): The webhook payload
        user_id (int, optional): Specific user ID to use, or None to find by account
        
    Returns:
        dict: Processing result
    """
    # This is very similar to transaction created, but we update the transaction
    # instead of creating a new one if it already exists
    return process_transaction_created(data, user_id)


@retry(exceptions=[Exception], tries=3, delay=1, backoff=2, jitter=0.1)
def process_transaction_deleted(data, user_id=None):
    """
    Process a TRANSACTION_DELETED webhook.
    
    Args:
        data (dict): The webhook payload
        user_id (int, optional): Specific user ID to use, or None to find by account
        
    Returns:
        dict: Processing result
    """
    # Extract transaction data
    try:
        transaction_data = data.get('data', {}).get('relationships', {}).get('transaction', {}).get('data', {})
        if not transaction_data or 'id' not in transaction_data:
            error_msg = "Missing transaction data in webhook"
            logger.error(error_msg)
            return {"success": False, "message": error_msg}
        
        external_id = transaction_data['id']
        logger.info(f"Processing transaction deleted event for transaction ID: {external_id}")
        
        # Find the user by account if not specified
        if not user_id:
            account_data = data.get('data', {}).get('relationships', {}).get('account', {}).get('data', {})
            if not account_data or 'id' not in account_data:
                error_msg = "Missing account data in webhook"
                logger.error(error_msg)
                return {"success": False, "message": error_msg}
            
            account_id = account_data['id']
            account = Account.query.filter_by(external_id=account_id).first()
            
            if not account:
                error_msg = f"Account not found: {account_id}"
                logger.error(error_msg)
                return {"success": False, "message": error_msg}
            
            user_id = account.user_id
        
        # Find the transaction
        transaction = Transaction.query.filter_by(
            external_id=external_id,
            user_id=user_id
        ).first()
        
        if not transaction:
            # Not an error, the transaction might have been deleted already
            logger.info(f"Transaction not found, already deleted: {external_id}")
            return {"success": True, "message": f"Transaction not found, already deleted: {external_id}"}
        
        # Store the week start date for recalculating summary
        week_start_date = transaction.week_start_date
        
        # Revert the account balance if needed
        if transaction.account_id:
            account = Account.query.get(transaction.account_id)
            if account:
                account.balance -= transaction.amount
                account.updated_at = datetime.utcnow()
        
        try:
            # Delete the transaction
            db.session.delete(transaction)
            db.session.commit()
            
            # Update weekly summary
            from app.models.transaction import WeeklySummary
            WeeklySummary.calculate_for_week(user_id, week_start_date)
            
            logger.info(f"Successfully deleted transaction: {external_id}")
            return {"success": True, "message": "Transaction deleted", "transaction_id": external_id}
        except Exception as db_error:
            db.session.rollback()
            error = handle_api_exception(db_error, "Database", "delete_transaction")
            logger.error(f"Database error deleting transaction: {error.message}")
            raise  # Retry the operation
            
    except Exception as e:
        error = handle_api_exception(e, "Webhook Processing", "process_transaction_deleted")
        logger.error(f"Error processing transaction deleted: {error.message}")
        raise  # Retry the operation


@retry(exceptions=[Exception], tries=3, delay=1, backoff=2, jitter=0.1)
def process_up_bank_transaction(transaction_data, user_id):
    """
    Process a transaction from Up Bank API.
    
    Args:
        transaction_data (dict): Transaction data from Up Bank API
        user_id (int): User ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    from app.services.transaction_service import process_and_save_upbank_transaction
    
    try:
        # Use the consolidated service function to process and save the transaction
        success, status, transaction = process_and_save_upbank_transaction(
            transaction_data, user_id
        )
        
        return success
    except Exception as e:
        logger.error(f"Error processing Up Bank transaction: {str(e)}")
        # Don't roll back here since we're outside the transaction
        raise  # Retry the operation