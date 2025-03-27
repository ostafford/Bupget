"""
Application factory module for the Budget App.

This module contains the application factory function that creates and 
configures the Flask application instance.
"""

import os
from flask import Flask

# Import configuration settings
from app.config import config_by_name

# Import extensions to be registered with the app
from app.extensions import db, migrate, login_manager

def create_app(config_name='development'):
    """
    Create and configure a Flask application instance.
    
    Args:
        config_name (str): The configuration to use - 'development', 'testing', or 'production'
                           Defaults to 'development'
    
    Returns:
        Flask: A configured Flask application instance
    """
    # Create the Flask app instance
    app = Flask(__name__)
    
    # Load configuration based on the specified environment
    app.config.from_object(config_by_name[config_name])
    
    # Initialize extensions with the app
    register_extensions(app)
    
    # Register blueprints (routes)
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register CLI commands
    from app.commands import register_commands
    register_commands(app)
    
    # Initialize encryption key
    with app.app_context():
        from app.utils.crypto import init_encryption_key
        init_encryption_key()
    
    # Return the configured app
    return app

def register_extensions(app):
    """
    Register Flask extensions with the application.
    
    Args:
        app (Flask): The Flask application instance
    """
    # Initialize SQLAlchemy with the app
    # This sets up the database connection and ORM functionality
    db.init_app(app)
    
    # Initialize Flask-Migrate with the app and db
    # This allows us to manage database migrations
    migrate.init_app(app, db)
    
    # Initialize Flask-Login for user authentication
    login_manager.init_app(app)
    
    # Configure login manager settings
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        # Import here to avoid circular import
        from app.models.user import User
        return User.query.get(int(user_id))

def register_blueprints(app):
    """
    Register blueprints (route modules) with the application.
    
    Args:
        app (Flask): The Flask application instance
    """
    # Import blueprints
    # Note: We import them here to avoid circular imports
    
    # This will be our main blueprint for non-authenticated pages
    from app.routes.main import main_bp
    app.register_blueprint(main_bp)
    
    # Authentication blueprint for login/register/etc
    from app.routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Dashboard blueprint for authenticated users
    from app.routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    
    # Transaction management blueprint
    from app.routes.transactions import transactions_bp
    app.register_blueprint(transactions_bp, url_prefix='/transactions')
    
    # Budget management blueprint
    from app.routes.budget import budget_bp
    app.register_blueprint(budget_bp, url_prefix='/budget')
    
    # API blueprint for the Up Bank integration
    from app.routes.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Up Bank integration blueprint
    from app.routes.up_bank import up_bank_bp
    app.register_blueprint(up_bank_bp, url_prefix='/up-bank')
    
    # Calendar view blueprint
    from app.routes.calendar import calendar_bp
    app.register_blueprint(calendar_bp, url_prefix='/calendar')

def register_error_handlers(app):
    """
    Register error handlers with the application.
    
    Args:
        app (Flask): The Flask application instance
    """
    @app.errorhandler(404)
    def page_not_found(e):
        return 'Page not found', 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return 'Internal server error', 500
