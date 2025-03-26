"""
Flask extensions initialization.

This module initializes Flask extensions used by the application.
Extensions are initialized without being bound to a specific application instance,
allowing them to be registered with the application in the factory function.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# SQLAlchemy extension for ORM functionality
# This provides database connectivity and object-relational mapping
db = SQLAlchemy()

# Flask-Migrate for database migrations
# This allows us to evolve the database schema over time
migrate = Migrate()

# Flask-Login for user authentication
# This provides user session management
login_manager = LoginManager()
