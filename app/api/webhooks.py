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
from app.api.up_bank import get_up_bank_api

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
        return False
    
    # Create a signature using HMAC with SHA256
    computed_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        request_data,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(computed_signature, signature)

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
            return {"success": False, "message": "Invalid webhook payload: missing eventType"}
        
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
        logger.error(f"Error processing webhook: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

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
            return {"success": False, "message": "Missing transaction data in webhook"}
        
        transaction_id = transaction_data['id']
        logger.info(f"Processing transaction created event for transaction ID: {transaction_id}")
        
        # Find the user by account if not specified
        if not user_id:
            account_data = data.get('data', {}).get('relationships', {}).get('account', {}).get('data', {})
            if not account_data or 'id' not in account_data:
                return {"success": False, "message": "Missing account data in webhook"}
            
            account_id = account_data['id']
            account = Account.query.filter_by(external_id=account_id).first()
            
            if not account:
                return {"success": False, "message": f"Account not found: {account_id}"}
            
            user_id = account.user_id
        
        # Get the user
        user = User.query.get(user_id)
        if not user:
            return {"success": False, "message": f"User not found: {user_id}"}
        
        # Get the Up Bank token for this user
        token = user.get_up_bank_token()
        if not token:
            return {"success": False, "message": f"Up Bank token not found for user: {user_id}"}
        
        # Get the Up Bank API
        api = get_up_bank_api(token=token)
        
        # Get the transaction from Up Bank
        transaction = api.get_transaction_by_id(transaction_id)
        if not transaction:
            return {"success": False, "message": f"Failed to retrieve transaction: {transaction_id}"}
        
        # Process the transaction (similar to sync logic)
        result = process_up_bank_transaction(transaction, user_id)
        
        if result:
            return {"success": True, "message": "Transaction created", "transaction_id": transaction_id}
        else:
            return {"success": False, "message": "Failed to process transaction"}
            
    except Exception as e:
        logger.error(f"Error processing transaction created: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

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
            return {"success": False, "message": "Missing transaction data in webhook"}
        
        external_id = transaction_data['id']
        logger.info(f"Processing transaction deleted event for transaction ID: {external_id}")
        
        # Find the user by account if not specified
        if not user_id:
            account_data = data.get('data', {}).get('relationships', {}).get('account', {}).get('data', {})
            if not account_data or 'id' not in account_data:
                return {"success": False, "message": "Missing account data in webhook"}
            
            account_id = account_data['id']
            account = Account.query.filter_by(external_id=account_id).first()
            
            if not account:
                return {"success": False, "message": f"Account not found: {account_id}"}
            
            user_id = account.user_id
        
        # Find the transaction
        transaction = Transaction.query.filter_by(
            external_id=external_id,
            user_id=user_id
        ).first()
        
        if not transaction:
            return {"success": True, "message": f"Transaction not found, already deleted: {external_id}"}
        
        # Store the week start date for recalculating summary
        week_start_date = transaction.week_start_date
        
        # Revert the account balance if needed
        if transaction.account_id:
            account = Account.query.get(transaction.account_id)
            if account:
                account.balance -= transaction.amount
                account.updated_at = datetime.utcnow()
        
        # Delete the transaction
        db.session.delete(transaction)
        db.session.commit()
        
        # Update weekly summary
        from app.models.transaction import WeeklySummary
        WeeklySummary.calculate_for_week(user_id, week_start_date)
        
        return {"success": True, "message": "Transaction deleted", "transaction_id": external_id}
            
    except Exception as e:
        logger.error(f"Error processing transaction deleted: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

def process_up_bank_transaction(transaction_data, user_id):
    """
    Process a transaction from Up Bank API.
    
    Args:
        transaction_data (dict): Transaction data from Up Bank API
        user_id (int): User ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Similar to the logic in sync_transactions but for a single transaction
    from app.models import Transaction, TransactionSource, Account, TransactionCategory
    
    try:
        # Extract the transaction ID
        tx_id = transaction_data.get('id')
        if not tx_id:
            logger.error("Transaction ID not found in data")
            return False
        
        # Extract transaction details from attributes
        attributes = transaction_data.get('attributes', {})
        
        # Get transaction description
        description = attributes.get('description', 'Unknown transaction')
        
        # Try to get a more meaningful description
        if 'rawText' in attributes and attributes['rawText']:
            description = attributes['rawText']
        
        # Extract date
        created_at = attributes.get('createdAt')
        if not created_at:
            logger.error("Transaction date not found")
            return False
            
        try:
            tx_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
        except (ValueError, TypeError, AttributeError):
            tx_date = datetime.now().date()
        
        # Extract amount
        amount_data = attributes.get('amount', {})
        value = amount_data.get('value', '0')
        
        try:
            amount = float(value)
        except (ValueError, TypeError):
            amount = 0.0
        
        # Determine account ID
        account_id = None
        relationships = transaction_data.get('relationships', {})
        account_data = relationships.get('account', {}).get('data', {})
        
        if account_data and 'id' in account_data:
            external_account_id = account_data['id']
            account = Account.query.filter_by(
                external_id=external_account_id,
                user_id=user_id
            ).first()
            
            if account:
                account_id = account.id
        
        # Check if transaction already exists
        existing_tx = Transaction.query.filter_by(
            external_id=tx_id,
            user_id=user_id
        ).first()
        
        if existing_tx:
            # Update existing transaction
            existing_tx.description = description
            existing_tx.amount = amount
            existing_tx.date = tx_date
            existing_tx.account_id = account_id
            existing_tx.updated_at = datetime.utcnow()
            
            # If category not already set, try to categorize
            if not existing_tx.category_id:
                from app.services.transaction_service import suggest_category_for_transaction
                category_id = suggest_category_for_transaction(description, user_id)
                if category_id:
                    existing_tx.category_id = category_id
            
            db.session.commit()
            
            # Update account balance if needed
            if account_id:
                account = Account.query.get(account_id)
                if account:
                    # Calculate balance change
                    account.updated_at = datetime.utcnow()
                    db.session.commit()
            
            # Update weekly summary
            from app.models.transaction import WeeklySummary
            WeeklySummary.calculate_for_week(user_id, existing_tx.week_start_date)
            
            return True
        else:
            # Create new transaction
            # Try to categorize the transaction
            from app.services.transaction_service import suggest_category_for_transaction
            category_id = suggest_category_for_transaction(description, user_id)
            
            new_tx = Transaction(
                external_id=tx_id,
                date=tx_date,
                description=description,
                amount=amount,
                source=TransactionSource.UP_BANK,
                user_id=user_id,
                account_id=account_id,
                category_id=category_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(new_tx)
            db.session.commit()
            
            # Update account balance if needed
            if account_id:
                account = Account.query.get(account_id)
                if account:
                    account.balance += amount
                    account.updated_at = datetime.utcnow()
                    db.session.commit()
            
            # Update weekly summary
            from app.models.transaction import WeeklySummary
            WeeklySummary.calculate_for_week(user_id, new_tx.week_start_date)
            
            return True
    
    except Exception as e:
        logger.error(f"Error processing Up Bank transaction: {str(e)}")
        db.session.rollback()
        return False
