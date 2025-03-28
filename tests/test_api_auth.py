"""
Tests for Up Bank API authentication.

This module contains tests for the Up Bank API authentication functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
from app import create_app
from app.extensions import db
from app.models import User
from app.api.up_bank import UpBankAPI, test_api_connection
from app.services.auth_service import validate_up_bank_token, store_up_bank_token


class TestUpBankAuth(unittest.TestCase):
    """Test cases for Up Bank API authentication."""
    
    def setUp(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create a test user
        self.user = User(
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        self.user.password = 'password'
        db.session.add(self.user)
        db.session.commit()
        
        # Test token
        self.test_token = 'up:yeah:test-token'
    
    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    @patch('app.api.up_bank.requests.get')
    def test_validate_token_success(self, mock_get):
        """Test validating a valid token."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"id": "ping"}}
        mock_get.return_value = mock_response
        
        # Test the validation
        api = UpBankAPI(token=self.test_token)
        result = api.validate_token()
        
        # Check the result
        self.assertTrue(result['valid'])
        self.assertEqual(result['message'], 'Token is valid')
        
        # Verify the mock was called with the right arguments
        mock_get.assert_called_once_with(
            'https://api.up.com.au/api/v1/util/ping',
            headers={'Authorization': f'Bearer {self.test_token}', 'Accept': 'application/json'}
        )
    
    @patch('app.api.up_bank.requests.get')
    def test_validate_token_failure(self, mock_get):
        """Test validating an invalid token."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"errors": [{"status": "401", "detail": "Invalid token"}]}
        mock_get.return_value = mock_response
        
        # Test the validation
        api = UpBankAPI(token='invalid-token')
        result = api.validate_token()
        
        # Check the result
        self.assertFalse(result['valid'])
        self.assertEqual(result['message'], 'Token is invalid or expired')
    
    @patch('app.api.up_bank.requests.get')
    def test_ping_success(self, mock_get):
        """Test pinging the API successfully."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Test the ping
        api = UpBankAPI(token=self.test_token)
        result = api.ping()
        
        # Check the result
        self.assertTrue(result)
    
    @patch('app.api.up_bank.requests.get')
    def test_ping_failure(self, mock_get):
        """Test pinging the API unsuccessfully."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        
        # Test the ping
        api = UpBankAPI(token='invalid-token')
        result = api.ping()
        
        # Check the result
        self.assertFalse(result)
    
    @patch('app.services.auth_service.validate_up_bank_token')
    def test_store_token_valid(self, mock_validate):
        """Test storing a valid token."""
        # Mock the validation result
        mock_validate.return_value = {"valid": True, "message": "Token is valid"}
        
        # Test storing the token
        result = store_up_bank_token(self.user.id, self.test_token)
        
        # Check the result
        self.assertTrue(result)
        
        # Verify the user has the token
        user = User.query.get(self.user.id)
        self.assertIsNotNone(user.up_bank_token)
        self.assertIsNotNone(user.up_bank_connected_at)
        
        # Verify the token is accessible
        token = user.get_up_bank_token()
        self.assertEqual(token, self.test_token)
    
    @patch('app.services.auth_service.validate_up_bank_token')
    def test_store_token_invalid(self, mock_validate):
        """Test storing an invalid token."""
        # Mock the validation result
        mock_validate.return_value = {"valid": False, "message": "Token is invalid"}
        
        # Test storing the token
        result = store_up_bank_token(self.user.id, 'invalid-token')
        
        # Check the result
        self.assertFalse(result)
        
        # Verify the user doesn't have the token
        user = User.query.get(self.user.id)
        self.assertIsNone(user.up_bank_connected_at)
    
    def test_store_token_user_not_found(self):
        """Test storing a token for a non-existent user."""
        # Test storing the token
        result = store_up_bank_token(999, self.test_token)
        
        # Check the result
        self.assertFalse(result)
    
    @patch('app.api.up_bank.requests.get')
    def test_test_api_connection(self, mock_get):
        """Test the API connection test function."""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Test the connection
        result = test_api_connection(self.test_token)
        
        # Check the result
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
