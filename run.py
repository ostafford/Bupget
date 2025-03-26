"""
Application entry point.

This module is the entry point for running the application.
It creates and runs a Flask application instance using the factory function.
"""

import os
from app import create_app

# Determine which configuration to use
# The FLASK_ENV environment variable can be set to 'development', 'testing',
# or 'production' to specify which configuration to use
config_name = os.environ.get('FLASK_ENV', 'development')

# Create an application instance with the specified configuration
app = create_app(config_name)

if __name__ == '__main__':
    # Run the application only if this script is executed directly
    # This allows us to import the app for testing without running it
    
    # Get the port from the PORT environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run the application with debug mode enabled in development
    app.run(
        host='0.0.0.0',  # Listen on all network interfaces
        port=port,       # Use the specified port
        debug=(config_name == 'development')  # Enable debug mode in development
    )
