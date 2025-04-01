"""
Up Bank error handling test commands.

This module provides commands for testing the error handling and retry
mechanisms of the Up Bank API integration.
"""

import click
import time
import traceback
from flask.cli import with_appcontext
from requests.exceptions import ConnectionError, Timeout, HTTPError


@click.command('test-upbank-error-handling')
@click.argument('user_id', type=int)
@click.option('--error-type', 
              type=click.Choice(['connection', 'timeout', 'auth', 'rate-limit', 'server']), 
              default='connection',
              help='Type of error to simulate')
@click.option('--retry-count', default=3, help='Number of retries to attempt')
@with_appcontext
def test_upbank_error_handling_command(user_id, error_type, retry_count):
    """
    Test Up Bank API error handling and retry mechanism.
    
    Args:
        user_id: The user ID to use for testing
        error_type: Type of error to simulate
        retry_count: Number of retries to attempt
    """
    from app.models import User
    from app.api.up_bank import get_up_bank_api, UpBankAuthError, UpBankRateLimitError, UpBankConnectionError
    
    # Get the user
    user = User.query.get(user_id)
    if not user:
        click.echo(f"User with ID {user_id} not found.")
        return
    
    # Get the token
    token = user.get_up_bank_token()
    if not token:
        click.echo("Up Bank token not found for user.")
        return
    
    # Create the fake API client with mocked error handling
    api = get_up_bank_api(token=token)
    
    # Define a test function that simulates errors
    def test_with_simulated_errors(api, error_type, retry_count):
        """Simulate different types of errors and test retry handling."""
        from app.utils.retry import retry
        
        # Keep track of call count
        call_counter = {'count': 0}
        
        @retry(
            exceptions=[ConnectionError, Timeout, UpBankConnectionError, UpBankRateLimitError, Exception],
            tries=retry_count + 1,  # +1 because first try is not a retry
            delay=1,
            backoff=2,
            jitter=0.1
        )
        def simulated_error_function():
            """Function that will raise specified errors up to retry_count times."""
            # Increment call counter
            call_counter['count'] += 1
            click.echo(f"\nAttempt #{call_counter['count']}...")
            
            # Only succeed on the last attempt
            if call_counter['count'] > retry_count:
                click.echo(f"✅ Success on attempt #{call_counter['count']}!")
                return True
            
            # Otherwise simulate the specified error
            click.echo(f"⚠️ Simulating {error_type} error...")
            
            # Sleep briefly to make the output more readable
            time.sleep(0.5)
            
            if error_type == 'connection':
                error = ConnectionError("Simulated connection error")
                click.echo(f"❌ Connection error: {str(error)}")
                raise error
                
            elif error_type == 'timeout':
                error = Timeout("Simulated timeout error")
                click.echo(f"❌ Timeout error: {str(error)}")
                raise error
                
            elif error_type == 'auth':
                error = UpBankAuthError("Simulated authentication error")
                click.echo(f"❌ Authentication error: {str(error)}")
                raise error
                
            elif error_type == 'rate-limit':
                error = UpBankRateLimitError(
                    "Simulated rate limit error",
                    retry_after=2,
                    status_code=429
                )
                click.echo(f"❌ Rate limit error: {str(error)}")
                raise error
                
            elif error_type == 'server':
                error = HTTPError("Simulated server error")
                click.echo(f"❌ Server error: {str(error)}")
                raise error
        
        # Run the test function with retry
        try:
            result = simulated_error_function()
            click.echo("\n🎉 Test completed successfully!")
            return result
        except Exception as e:
            click.echo(f"\n❌ Test failed after {call_counter['count']} attempts")
            click.echo(f"Final error: {str(e)}")
            return False
    
    # Run the test
    click.echo(f"Testing Up Bank error handling for user {user.full_name} (ID: {user_id})")
    click.echo(f"Error type: {error_type}")
    click.echo(f"Retry count: {retry_count}")
    click.echo("\nStarting test...")
    
    start_time = time.time()
    result = test_with_simulated_errors(api, error_type, retry_count)
    end_time = time.time()
    
    # Show summary
    click.echo("\n=== Test Summary ===")
    click.echo(f"Overall result: {'Success' if result else 'Failure'}")
    click.echo(f"Total time: {end_time - start_time:.2f} seconds")
    
    if result:
        click.echo(f"\nRetry mechanism successfully handled {error_type} errors after {retry_count} retries.")
    else:
        click.echo(f"\nRetry mechanism failed to handle {error_type} errors after {retry_count} retries.")
        
        if error_type == 'auth':
            click.echo("Note: Authentication errors are not retried by design, as retrying with the same token will not help.")


@click.command('test-upbank-webhook-retry')
@click.argument('user_id', type=int)
@click.option('--transaction-id', help='External transaction ID to use')
@click.option('--error-type', 
              type=click.Choice(['connection', 'timeout', 'auth', 'rate-limit', 'server', 'db']), 
              default='connection',
              help='Type of error to simulate')
@click.option('--retry-count', default=3, help='Number of retries to attempt')
@with_appcontext
def test_upbank_webhook_retry_command(user_id, transaction_id, error_type, retry_count):
    """
    Test Up Bank webhook retry mechanism.
    
    Args:
        user_id: The user ID to use for testing
        transaction_id: External transaction ID to use
        error_type: Type of error to simulate
        retry_count: Number of retries to attempt
    """
    import json
    from app.models import User, Account, Transaction
    from app.api.webhooks import process_webhook
    
    # Get the user
    user = User.query.get(user_id)
    if not user:
        click.echo(f"User with ID {user_id} not found.")
        return
    
    # Get an account for this user
    account = Account.query.filter_by(user_id=user_id).first()
    if not account:
        click.echo(f"No accounts found for user {user.full_name}.")
        return
    
    # Get a transaction if not specified
    if not transaction_id:
        transaction = Transaction.query.filter_by(user_id=user_id).first()
        if not transaction:
            click.echo("No transactions found. Please provide a transaction-id.")
            return
        
        transaction_id = transaction.external_id or 'test-transaction-id'
    
    # Create simulated webhook data
    webhook_data = {
        "data": {
            "type": "webhook-events",
            "id": "test-webhook-event-id",
            "attributes": {
                "eventType": "TRANSACTION_CREATED",
                "createdAt": "2023-06-13T10:00:00+10:00"
            },
            "relationships": {
                "webhook": {
                    "data": {
                        "type": "webhooks",
                        "id": "test-webhook-id"
                    }
                },
                "transaction": {
                    "data": {
                        "type": "transactions",
                        "id": transaction_id
                    }
                },
                "account": {
                    "data": {
                        "type": "accounts",
                        "id": account.external_id or 'test-account-id'
                    }
                }
            }
        }
    }
    
    # Mock the process_up_bank_transaction function to simulate errors
    original_process_transaction = None
    
    def mock_setup():
        """Set up mocking for the test."""
        nonlocal original_process_transaction
        from app.api import webhooks
        
        # Save the original function
        original_process_transaction = webhooks.process_up_bank_transaction
        
        # Create a counter to keep track of calls
        call_counter = {'count': 0}
        
        # Define the mock function
        def mock_process_transaction(*args, **kwargs):
            """Mock function that will simulate errors and eventually succeed."""
            # Increment call counter
            call_counter['count'] += 1
            click.echo(f"\nAttempt #{call_counter['count']} to process transaction...")
            
            # Only succeed on the last attempt
            if call_counter['count'] > retry_count:
                click.echo(f"✅ Success on attempt #{call_counter['count']}!")
                return True
            
            # Otherwise simulate the specified error
            click.echo(f"⚠️ Simulating {error_type} error...")
            
            # Sleep briefly to make the output more readable
            time.sleep(0.5)
            
            if error_type == 'connection':
                error = ConnectionError("Simulated connection error")
                click.echo(f"❌ Connection error: {str(error)}")
                raise error
                
            elif error_type == 'timeout':
                error = Timeout("Simulated timeout error")
                click.echo(f"❌ Timeout error: {str(error)}")
                raise error
                
            elif error_type == 'auth':
                from app.api.up_bank import UpBankAuthError
                error = UpBankAuthError("Simulated authentication error")
                click.echo(f"❌ Authentication error: {str(error)}")
                raise error
                
            elif error_type == 'rate-limit':
                from app.api.up_bank import UpBankRateLimitError
                error = UpBankRateLimitError(
                    "Simulated rate limit error",
                    retry_after=2,
                    status_code=429
                )
                click.echo(f"❌ Rate limit error: {str(error)}")
                raise error
                
            elif error_type == 'server':
                error = HTTPError("Simulated server error")
                click.echo(f"❌ Server error: {str(error)}")
                raise error
                
            elif error_type == 'db':
                from sqlalchemy.exc import SQLAlchemyError
                error = SQLAlchemyError("Simulated database error")
                click.echo(f"❌ Database error: {str(error)}")
                raise error
        
        # Replace the original function with our mock
        webhooks.process_up_bank_transaction = mock_process_transaction
        
        return call_counter
    
    def mock_teardown():
        """Remove mocking after the test."""
        from app.api import webhooks
        
        # Restore the original function
        if original_process_transaction:
            webhooks.process_up_bank_transaction = original_process_transaction
    
    # Run the test
    click.echo(f"Testing Up Bank webhook retry for user {user.full_name} (ID: {user_id})")
    click.echo(f"Transaction ID: {transaction_id}")
    click.echo(f"Error type: {error_type}")
    click.echo(f"Retry count: {retry_count}")
    click.echo("\nStarting test...")
    
    try:
        # Set up mocking
        call_counter = mock_setup()
        
        # Process the webhook
        start_time = time.time()
        result = process_webhook(webhook_data, user_id)
        end_time = time.time()
        
        # Show summary
        click.echo("\n=== Test Summary ===")
        click.echo(f"Webhook result: {json.dumps(result, indent=2)}")
        click.echo(f"Attempts made: {call_counter['count']}")
        click.echo(f"Total time: {end_time - start_time:.2f} seconds")
        
        if result.get('success'):
            click.echo(f"\nRetry mechanism successfully handled {error_type} errors after {retry_count} retries.")
        else:
            click.echo(f"\nRetry mechanism failed to handle {error_type} errors after {retry_count} retries.")
            
            if error_type == 'auth':
                click.echo("Note: Authentication errors are not retried by design, as retrying with the same token will not help.")
    finally:
        # Always restore the original function
        mock_teardown()


def register_upbank_test_commands(app):
    """Register Up Bank test CLI commands with the Flask application."""
    app.cli.add_command(test_upbank_error_handling_command)
    app.cli.add_command(test_upbank_webhook_retry_command)
