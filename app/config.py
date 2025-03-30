"""
Application configuration settings.

This module defines different configuration classes for various environments
(development, testing, production).
"""

import os
from datetime import timedelta

# Load environment variables from .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class Config:
    """Base configuration class with settings common to all environments."""
    
    # Secret key for securing session cookies and CSRF tokens
    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a-very-secret-key')
    
    # Database settings - using MySQL
    # SQLAlchemy will use these settings to connect to the database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI')
    
    # Disable SQLAlchemy modification tracking to save resources
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Up Bank API settings
    UP_BANK_API_URL = 'https://api.up.com.au/api/v1'
    UP_BANK_API_TOKEN = os.environ.get('UP_BANK_API_TOKEN')
    
    # Flask-Login settings
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    
    # Default currency for the application
    DEFAULT_CURRENCY = 'AUD'
    
    # Error logging
    LOG_LEVEL = 'INFO'

class DevelopmentConfig(Config):
    """Development environment configuration."""
    
    # Debug mode enables features helpful during development
    DEBUG = True
    
    # More verbose logging for development
    LOG_LEVEL = 'DEBUG'
    
    # Use SQLite for development - it's simple and doesn't require a server
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI', 'sqlite:///dev.db')

class TestingConfig(Config):
    """Testing environment configuration."""
    
    # Testing mode
    TESTING = True
    
    # Use in-memory SQLite for tests to avoid file dependencies
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF protection in tests for simplicity
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Production environment configuration."""
    
    # No debug mode in production
    DEBUG = False
    
    # Use a more secure secret key in production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Ensure the database URI is set from environment variables
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI')
    
    # Production should use HTTPS
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    
    # Additional security settings
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True

# Mapping from string names to configuration classes
# This allows us to select the configuration by name
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}
