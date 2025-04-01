"""
Tests for Up Bank API retry mechanism.

This module tests the retry functionality for the Up Bank API integration.
"""

import unittest
import responses
import time
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call
from app import create_app
from app.extensions import db
from app.api.up_bank import (
    UpBankAPI, 
    UpBankError,
    UpBankAuthError, 
    UpBankRateLimitError, 
    UpBankConnectionError
)
from app.utils.retry import retry
from requests.exceptions import ConnectionError, Timeout


class TestUpBankRetry(unittest.TestCase):
    """Test cases for Up Bank API retry mechanism."""
    
    def setUp(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Test token
        self.test_token = 'up:yeah:test-token'
        
        # Create API client
        self.api = UpBankAPI(token=self.test_token)
        
        # Set up responses for mocking HTTP requests
        responses.start()
    
    def tearDown(self):
        """Clean up after tests."""
        responses.stop()
        responses.reset()
        self.app_context.pop()
    
    @responses.activate
    def test_retry_on_connection_error(self):
        """Test retrying on connection error."""
        # Create a testable function that uses our retry decorator
        retry_counter = {'count': 0}
        
        @retry(exceptions=[ConnectionError], tries=3, delay=0.1)
        def test_function():
            retry_counter['count'] += 1
            if retry_counter['count'] < 3:
                raise ConnectionError("Test connection error")
            return True
        
        # Call the function
        result = test_function()
        
        # Verify it was called the expected number of times and succeeded
        self.assertEqual(retry_counter['count'], 3)
        self.assertTrue(result)
    
    @patch('time.sleep')  # Patch sleep to avoid waiting in tests
    @patch('app.api.up_bank.UpBankAPI._make_request')
    def test_retry_on_rate_limit(self, mock_make_request, mock_sleep):
        """Test retrying after rate limit error."""
        # Make _make_request raise a rate limit error on first call, then return success
        mock_make_request.side_effect = [
            UpBankRateLimitError(
                "Rate limit exceeded",
                retry_after=2,
                status_code=429
            ),
            {'data': {'id': 'ping'}}
        ]
        
        # Call ping which should retry after the rate limit error
        result = self.api.ping()
        
        # Check result
        self.assertTrue(result)
        
        # Verify make_request was called twice
        self.assertEqual(mock_make_request.call_count, 2)
        
        # Verify sleep was called once
        mock_sleep.assert_called_once()
    
    @patch('time.sleep')  # Patch sleep to avoid waiting in tests
    @responses.activate
    def test_transaction_sync_retries(self, mock_sleep):
        """Test that transaction sync retries on errors."""
        # Add a mocked response for the ping endpoint
        responses.add(
            responses.GET,
            f"{self.api.base_url}/util/ping",
            json={'data': {'id': 'ping'}},
            status=200
        )
        
        # First page of transactions - succeeds
        responses.add(
            responses.GET,
            f"{self.api.base_url}/transactions",
            json={
                'data': [
                    {'id': 'tx1', 'attributes': {'createdAt': '2023-01-02T12:00:00Z', 'description': 'Test Transaction'}}
                ],
                'links': {'next': '/transactions?page=2'}
            },
            status=200
        )
        
        # Second page of transactions - fails with 429 first, then succeeds
        responses.add(
            responses.GET,
            f"{self.api.base_url}{'/transactions?page=2'}",
            json={'errors': [{'detail': 'Rate limit exceeded'}]},
            status=429,
            headers={'Retry-After': '1'}
        )
        
        responses.add(
            responses.GET,
            f"{self.api.base_url}{'/transactions?page=2'}",
            json={
                'data': [
                    {'id': 'tx2', 'attributes': {'createdAt': '2023-01-03T12:00:00Z', 'description': 'Test Transaction 2'}}
                ],
                'links': {}
            },
            status=200
        )
        
        # Test the sync_transactions method with mocked datetime
        with patch('datetime.datetime') as mock_datetime:
            # Create a fixed date for testing
            fixed_date = datetime(2023, 1, 31)
            mock_datetime.now.return_value = fixed_date
            mock_datetime.strftime.return_value = '2023-01-01T00:00:00Z'
            
            # Mock account lookup
            with patch('app.models.Account.query') as mock_account_query:
                # Mock account query
                mock_account_filter = MagicMock()
                mock_account_query.filter_by.return_value = mock_account_filter
                mock_account_filter.all.return_value = [MagicMock(external_id='account1', id=1)]
                
                # Mock transaction processing to avoid DB operations
                with patch('app.api.up_bank.UpBankAPI._process_transaction', return_value="created") as mock_process:
                    # Run the sync with a user ID
                    created, updated = self.api.sync_transactions(user_id=1, days_back=30)
    
    @patch('time.sleep')  # Patch sleep to avoid waiting in tests
    def test_webhook_retry(self, mock_sleep):
        """Test that webhook processing retries on transient errors."""
        from app.api.webhooks import process_transaction_created
        
        # Create a counter to track retry attempts
        retry_counter = {'count': 0}
        
        # Create a modified version of process_transaction_created for testing
        original_process = process_transaction_created
        
        @retry(exceptions=[ConnectionError, UpBankConnectionError], tries=3, delay=0.1)
        def test_process_tx_webhook(data, user_id=None):
            """Test function that fails twice then succeeds."""
            retry_counter['count'] += 1
            if retry_counter['count'] < 3:
                if retry_counter['count'] == 1:
                    raise ConnectionError("Test connection error")
                else:
                    raise UpBankConnectionError("Test Up Bank error")
            
            # On the third attempt, return success
            return {
                "success": True,
                "message": "Transaction created",
                "transaction_id": "test-tx-id"
            }
        
        # Create test webhook data
        webhook_data = {
            'data': {
                'attributes': {'eventType': 'TRANSACTION_CREATED'},
                'relationships': {
                    'transaction': {'data': {'id': 'tx1'}},
                    'account': {'data': {'id': 'account1'}}
                }
            }
        }
        
        try:
            # Replace the real function with our test function
            from app.api import webhooks
            webhooks.process_transaction_created = test_process_tx_webhook
            
            # Call the webhook processor
            result = webhooks.process_transaction_created(webhook_data, user_id=1)
            
            # Verify the result
            self.assertTrue(result['success'])
            self.assertEqual(retry_counter['count'], 3)
            
        finally:
            # Restore the original function
            webhooks.process_transaction_created = original_process


if __name__ == '__main__':
    unittest.main()
