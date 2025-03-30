"""
CLI command for testing Up Bank webhooks.

This module provides commands to test webhook processing locally.
"""

import json
import click
from flask.cli import with_appcontext
from app.api.webhooks import process_webhook
from app.models import User, Account, Transaction

@click.command('test-webhook')
@click.argument('user_id', type=int)
@click.argument('event_type', type=click.Choice(['TRANSACTION_CREATED', 'TRANSACTION_SETTLED', 'TRANSACTION_DELETED']))
@click.option('--transaction-id', help='External transaction ID for TRANSACTION_DELETED')
@with_appcontext
def test_webhook_command(user_id, event_type, transaction_id):
    """
    Test webhook processing with a simulated webhook payload.
    
    Args:
        user_id: The user ID
        event_type: Type of webhook event
        transaction_id: External transaction ID (for TRANSACTION_DELETED)
    """
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
    
    # Get a transaction for TRANSACTION_DELETED if not specified
    if event_type == 'TRANSACTION_DELETED' and not transaction_id:
        transaction = Transaction.query.filter_by(
            user_id=user_id,
            external_id=transaction_id
        ).first()
        
        if not transaction:
            click.echo("No transactions found with external ID. Please provide a valid transaction-id.")
            return
        
        transaction_id = transaction.external_id
    elif event_type != 'TRANSACTION_DELETED':
        # For other event types, get the most recent transaction
        transaction = Transaction.query.filter_by(
            user_id=user_id,
            account_id=account.id
        ).order_by(Transaction.created_at.desc()).first()
        
        if transaction and transaction.external_id:
            transaction_id = transaction.external_id
        else:
            click.echo("No transactions found for testing. Please sync transactions first.")
            return
    
    # Create simulated webhook payload
    click.echo(f"Creating simulated {event_type} webhook for user {user.full_name}...")
    
    webhook_data = {
        "data": {
            "type": "webhook-events",
            "id": "test-webhook-event-id",
            "attributes": {
                "eventType": event_type,
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
                        "id": account.external_id
                    }
                }
            }
        }
    }
    
    # Process the webhook
    click.echo("Processing simulated webhook...")
    result = process_webhook(webhook_data, user_id)
    
    # Display result
    if result["success"]:
        click.echo(f"✅ Webhook processed successfully: {result['message']}")
    else:
        click.echo(f"❌ Webhook processing failed: {result['message']}")

@click.command('generate-webhook-secret')
@with_appcontext
def generate_webhook_secret_command():
    """Generate a secure webhook secret for Up Bank."""
    import secrets
    import base64
    
    # Generate a secure random secret
    secret_bytes = secrets.token_bytes(32)
    secret = base64.b64encode(secret_bytes).decode('utf-8')
    
    click.echo("Generated webhook secret:")
    click.echo(secret)
    click.echo("\nAdd this to your .env file as:")
    click.echo(f"UP_BANK_WEBHOOK_SECRET={secret}")

def register_webhook_commands(app):
    """Register webhook CLI commands with the Flask application."""
    app.cli.add_command(test_webhook_command)
    app.cli.add_command(generate_webhook_secret_command)
