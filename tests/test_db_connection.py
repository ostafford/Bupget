"""
Simple script to test PostgreSQL connection.
Run this from the command line to test your database connection.
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2

# Load environment variables from .env file
load_dotenv()

def test_connection():
    """Test connection to PostgreSQL database."""
    
    # Get connection string from environment
    database_uri = os.environ.get('DATABASE_URI')
    
    if not database_uri:
        print("ERROR: DATABASE_URI environment variable not found.")
        print("Make sure your .env file contains DATABASE_URI and is in the correct location.")
        return False
        
    print(f"Attempting to connect with URI: {database_uri}")
    
    try:
        # Parse the connection string
        # Expected format: postgresql://username:password@host:port/database
        if database_uri.startswith('postgresql://'):
            # Remove the protocol part
            conn_str = database_uri[len('postgresql://'):]
            
            # Split into parts
            user_pass, host_db = conn_str.split('@')
            
            if ':' in user_pass:
                username, password = user_pass.split(':', 1)
            else:
                username = user_pass
                password = ''
                
            if '/' in host_db:
                host_port, dbname = host_db.split('/', 1)
            else:
                host_port = host_db
                dbname = ''
                
            if ':' in host_port:
                host, port = host_port.split(':')
                port = int(port)
            else:
                host = host_port
                port = 5432  # Default PostgreSQL port
                
            print(f"Parsed connection parameters:")
            print(f"  Host: {host}")
            print(f"  Port: {port}")
            print(f"  Database: {dbname}")
            print(f"  Username: {username}")
            print(f"  Password: {'*' * len(password)}")
            
            # Connect to the database
            conn = psycopg2.connect(
                host=host,
                port=port,
                dbname=dbname,
                user=username,
                password=password
            )
            
            # Test the connection
            cur = conn.cursor()
            cur.execute('SELECT 1')
            result = cur.fetchone()
            
            cur.close()
            conn.close()
            
            print(f"SUCCESS: Successfully connected to PostgreSQL database! Test query returned: {result}")
            return True
            
        else:
            print("ERROR: DATABASE_URI does not start with 'postgresql://'")
            return False
            
    except Exception as e:
        print(f"ERROR: Connection failed with error: {str(e)}")
        
        # Provide helpful advice based on common errors
        if "password authentication failed" in str(e).lower():
            print("\nTIP: Your username or password might be incorrect.")
            print("Verify your PostgreSQL credentials with: psql -U your_username -d your_database")
        elif "could not connect to server" in str(e).lower():
            print("\nTIP: The PostgreSQL server might not be running or is not accessible.")
            print("Check if PostgreSQL is running with: sudo service postgresql status")
        elif "database" in str(e).lower() and "does not exist" in str(e).lower():
            print("\nTIP: The database doesn't exist. Create it with:")
            print(f"createdb -U {username} {dbname}")
        
        return False

if __name__ == "__main__":
    if test_connection():
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure
