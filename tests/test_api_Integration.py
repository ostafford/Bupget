"""
Advanced Unit Tests for Up Bank API Integration.

This test suite provides comprehensive testing for the Up Bank API,
covering complex scenarios, edge cases, and detailed interaction patterns.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timedelta
import requests
from requests.exceptions import ConnectionError, Timeout

from app import create_app
from app.extensions import db
from app.api.up_bank import (
    UpBankAPI, 
    UpBankError, 
    UpBankAuthError, 
    UpBankRateLimitError, 
    UpBankConnectionError,
    UpBankAPIError
)
from app.models import (
    User, 
    Transaction, 
    Account, 
    AccountType,  
    AccountSource,  
    TransactionSource
)


class TestUpBankAPIAdvanced(unittest.TestCase):
    """
    Comprehensive test suite for advanced Up Bank API interaction scenarios.
    """

    def setUp(self):
        """
        Prepare the test environment with a comprehensive setup.
        """
        # Create test application
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create test database
        db.create_all()
        
        # Create a test user
        self.test_user = User(
            email='advanced_test_upbank@example.com',
            first_name='Advanced',
            last_name='TestUser'
        )
        self.test_user.password = 'complexTestPassword123!'
        db.session.add(self.test_user)
        db.session.commit()
        
        # Test token for Up Bank API
        self.test_token = 'up:yeah:test-advanced-token'

    def tearDown(self):
        """
        Clean up the test environment after each test.
        """
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _create_mock_account(self, external_id='test_account_1', name='Test Account'):
        """
        Helper method to create a mock account for testing.
        """
        account = Account(
            external_id=external_id,
            name=name,
            type=AccountType.CHECKING,  # Use valid enum value
            source=AccountSource.UP_BANK,
            balance=1000.00,
            currency='AUD',
            user_id=self.test_user.id
        )
        db.session.add(account)
        db.session.commit()
        return account

    def test_account_balance_retrieval(self):
        """
        Test account balance retrieval with multiple scenarios.
        """
        # Prepare a mock account for testing
        test_account = self._create_mock_account()

        # Scenario 1: Successful single account balance
        with patch.object(UpBankAPI, '_make_request') as mock_request:
            # Mock account data with balance
            mock_account_data = {
                'data': {
                    'id': test_account.external_id,
                    'attributes': {
                        'displayName': test_account.name,
                        'balance': {
                            'value': '1500.00',
                            'currencyCode': 'AUD'
                        }
                    }
                }
            }
            mock_request.return_value = mock_account_data

            api = UpBankAPI(token=self.test_token)

            # Retrieve account balance
            balance = api.get_account_balance(test_account.external_id)

            # Assertions
            self.assertIsNotNone(balance)
            self.assertEqual(balance['value'], '1500.00')
            self.assertEqual(balance['currencyCode'], 'AUD')

        # Scenario 2: Multiple account balances
        with patch.object(UpBankAPI, 'get_accounts') as mock_get_accounts:
            # Mock multiple accounts with detailed attributes
            mock_accounts = [
                {
                    'id': 'account1', 
                    'attributes': {
                        'displayName': 'Account 1',
                        'balance': {'value': '1000.00', 'currencyCode': 'AUD'}
                    }
                },
                {
                    'id': 'account2', 
                    'attributes': {
                        'displayName': 'Account 2',
                        'balance': {'value': '2000.00', 'currencyCode': 'AUD'}
                    }
                }
            ]
            mock_get_accounts.return_value = mock_accounts

            api = UpBankAPI(token=self.test_token)

            # Retrieve all account balances
            balances = api.get_all_account_balances()

            # Assertions
            self.assertEqual(len(balances), 2)
            self.assertIn('account1', balances)
            self.assertIn('account2', balances)
            self.assertEqual(balances['account1']['value'], '1000.00')
            self.assertEqual(balances['account2']['value'], '2000.00')

    def test_error_recovery_and_retry_scenarios(self):
        """
        Test error recovery and retry mechanisms.
        """
        # Prepare a mock account for testing
        test_account = self._create_mock_account()

        # Scenario: Intermittent network failures during transaction sync
        with patch.object(UpBankAPI, '_make_request') as mock_request, \
             patch.object(UpBankAPI, '_process_transaction') as mock_process_transaction:
            # Create a counter to simulate retry behavior
            call_counter = {'count': 0, 'data_calls': 0}
            
            def intermittent_failure_side_effect(*args, **kwargs):
                call_counter['count'] += 1
                
                # First two calls fail, third succeeds
                if call_counter['count'] <= 2:
                    raise ConnectionError("Intermittent network failure")
                
                # Successful response after retries
                return {
                    'data': [
                        {
                            'id': 'tx_retry_success',
                            'attributes': {
                                'description': 'Retry Success Transaction',
                                'createdAt': '2023-06-15T12:00:00Z',
                                'amount': {'value': '-100.00'}
                            },
                            'relationships': {
                                'account': {'data': {'id': test_account.external_id}}
                            }
                        }
                    ],
                    'links': {}
                }
            
            mock_request.side_effect = intermittent_failure_side_effect
            mock_process_transaction.return_value = 'created'

            # Prepare API
            api = UpBankAPI(token=self.test_token)
            
            # Use a real user context
            with self.app_context:
                # Simulate sync with fixed user and days
                created, updated = api.sync_transactions(
                    user_id=self.test_user.id, 
                    days_back=30
                )
                
                # Verify successful sync after retries
                self.assertEqual(created, 1)
                self.assertEqual(updated, 0)
                
                # Verify retry mechanism worked
                self.assertEqual(call_counter['count'], 3)

    def test_sync_transactions_complex_scenarios(self):
        """
        Test transaction synchronization with complex scenarios.
        """
        # Prepare a mock account for testing
        test_account = self._create_mock_account()

        # Scenario: Multi-page transaction sync
        with patch.object(UpBankAPI, '_make_request') as mock_request, \
             patch.object(UpBankAPI, '_process_transaction') as mock_process_transaction:
            # Mock multi-page transaction responses
            def side_effect(*args, **kwargs):
                # First page
                if 'page=1' in str(args):
                    return {
                        'data': [
                            {
                                'id': 'tx1',
                                'attributes': {
                                    'description': 'Transaction 1',
                                    'createdAt': '2023-06-15T10:00:00Z',
                                    'amount': {'value': '-50.00'}
                                },
                                'relationships': {
                                    'account': {'data': {'id': test_account.external_id}}
                                }
                            }
                        ],
                        'links': {'next': '/transactions?page=2'}
                    }
                # Second page
                elif 'page=2' in str(args):
                    return {
                        'data': [
                            {
                                'id': 'tx2',
                                'attributes': {
                                    'description': 'Transaction 2',
                                    'createdAt': '2023-06-15T11:00:00Z',
                                    'amount': {'value': '-75.00'}
                                },
                                'relationships': {
                                    'account': {'data': {'id': test_account.external_id}}
                                }
                            }
                        ],
                        'links': {}  # No more pages
                    }
                # Default case
                return {'data': [], 'links': {}}
            
            mock_request.side_effect = side_effect

            # Mock process_transaction to simulate successful processing
            mock_process_transaction.side_effect = ['created', 'created']

            # Prepare API
            api = UpBankAPI(token=self.test_token)
            
            # Use a real user context
            with self.app_context:
                # Simulate sync with fixed user and days
                created, updated = api.sync_transactions(
                    user_id=self.test_user.id, 
                    days_back=30
                )
                
                # Verify sync results
                self.assertEqual(created, 2)  # Two transactions created
                self.assertEqual(updated, 0)

    def test_token_expiration_and_renewal(self):
        """
        Test token expiration and renewal scenarios.
        """
        # Scenario: Token expired
        with patch.object(UpBankAPI, '_make_request') as mock_request:
            # Simulate an expired token scenario
            mock_request.side_effect = UpBankAuthError("Token expired")

            api = UpBankAPI(token=self.test_token)
            
            # Validate token
            validation_result = api.validate_token()
            
            # Assertions
            self.assertFalse(validation_result['valid'])
            self.assertEqual(
                validation_result['message'], 
                'Token is invalid or expired'
            )

    def test_transaction_retrieval_scenarios(self):
        """
        Test comprehensive transaction retrieval scenarios.
        """
        # Scenario 1: Successful transaction retrieval
        with patch.object(UpBankAPI, '_make_request') as mock_request:
            # Mock a successful transaction response
            mock_transaction_data = {
                'data': {
                    'id': 'tx_test_123',
                    'attributes': {
                        'description': 'Test Transaction',
                        'createdAt': '2023-06-15T10:30:00Z',
                        'amount': {
                            'value': '-50.00',
                            'currencyCode': 'AUD'
                        },
                        'rawText': 'Detailed transaction description'
                    },
                    'relationships': {
                        'account': {
                            'data': {'id': 'account_test_1'}
                        }
                    }
                }
            }
            mock_request.return_value = mock_transaction_data

            # Create API instance
            api = UpBankAPI(token=self.test_token)
            
            # Retrieve transaction
            transaction = api.get_transaction_by_id('tx_test_123')
            
            # Assertions
            self.assertIsNotNone(transaction)
            self.assertEqual(transaction['id'], 'tx_test_123')
            self.assertEqual(
                transaction['attributes']['description'], 
                'Test Transaction'
            )


if __name__ == '__main__':
    unittest.main()
