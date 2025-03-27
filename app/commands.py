@click.command('test-upbank-auth')
@click.argument('token', required=True)
def test_upbank_auth_command(token):
    """
    Test authentication with the Up Bank API.
    
    Args:
        token: The Up Bank personal access token
    """
    from app.api.up_bank import test_api_connection
    
    result = test_api_connection(token)
    
    if result:
        click.echo("✅ Successfully authenticated with Up Bank API")
    else:
        click.echo("❌ Failed to authenticate with Up Bank API")


def register_commands(app):
    """Register CLI commands with the Flask application."""
    global app
    app = app  # Store app reference for verify-setup command
    
    app.cli.add_command(init_db_command)
    app.cli.add_command(drop_db_command)
    app.cli.add_command(create_demo_user_command)
    app.cli.add_command(verify_setup_command)
    app.cli.add_command(connect_up_bank_command)
    app.cli.add_command(sync_up_bank_command)
    app.cli.add_command(test_upbank_auth_command)
