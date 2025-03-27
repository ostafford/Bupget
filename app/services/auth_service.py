"""
Authentication service.

This module provides functions for handling user authentication
and external API authentication like Up Bank.
"""

import logging
from datetime import datetime
from app.models import User
from app.api.up_bank import get_up_bank_api
from app.extensions import db

# Configure logging
logger = logging.getLogger(__name__)


def validate_up_bank_token(token):
    """
    Validate an Up Bank token without storing it.
    
    Args:
        token (str): The Up Bank API token to validate
        
    Returns:
        dict: Validation result with status and message
    """
    try:
        # Initialize the API with the provided token
        api = get_up_bank_api(token)
        
        # Validate the token
        return api.validate_token()
    except Exception as e:
        logger.error(f"Error validating Up Bank token: {str(e)}")
        return {
            "valid": False,
            "message": f"Error: {str(e)}"
        }


def store_up_bank_token(user_id, token):
    """
    Store an Up Bank token for a user.
    
    Args:
        user_id (int): The user ID
        token (str): The Up Bank API token to store
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # First validate the token
        validation = validate_up_bank_token(token)
        
        if not validation["valid"]:
            logger.error(f"Failed to store invalid Up Bank token: {validation['message']}")
            return False
        
        # Get the user
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return False
        
        # Store the token
        user.set_up_bank_token(token)
        
        # Update last connected timestamp
        user.up_bank_connected_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Successfully stored Up Bank token for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error storing Up Bank token: {str(e)}")
        return False


def clear_up_bank_token(user_id):
    """
    Clear the stored Up Bank token for a user.
    
    Args:
        user_id (int): The user ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the user
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return False
        
        # Clear the token
        user.set_up_bank_token(None)
        
        # Clear connected timestamp
        user.up_bank_connected_at = None
        db.session.commit()
        
        logger.info(f"Successfully cleared Up Bank token for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error clearing Up Bank token: {str(e)}")
        return False


def get_up_bank_connection_status(user_id):
    """
    Check if a user has a valid Up Bank connection.
    
    Args:
        user_id (int): The user ID
        
    Returns:
        dict: Connection status with connected flag and details
    """
    try:
        # Get the user
        user = User.query.get(user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            return {
                "connected": False,
                "message": "User not found"
            }
        
        # Check if user has a token
        token = user.get_up_bank_token()
        if not token:
            return {
                "connected": False,
                "message": "No Up Bank token found"
            }
        
        # Validate the token
        api = get_up_bank_api(token)
        validation = api.validate_token()
        
        if validation["valid"]:
            return {
                "connected": True,
                "message": "Connected to Up Bank",
                "connected_at": user.up_bank_connected_at.isoformat() if user.up_bank_connected_at else None
            }
        else:
            return {
                "connected": False,
                "message": validation["message"]
            }
    except Exception as e:
        logger.error(f"Error checking Up Bank connection status: {str(e)}")
        return {
            "connected": False,
            "message": f"Error: {str(e)}"
        }
