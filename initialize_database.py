"""
Database initialization script.

This script helps set up the PostgreSQL database for the Budget App.
It performs checks and creates necessary users and databases if they don't exist.
"""

import os
import sys
import subprocess
import getpass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_psql_command(command, as_postgres=True):
    """Run a PostgreSQL command."""
    if as_postgres:
        cmd = ['sudo', '-u', 'postgres', 'psql', '-c', command]
    else:
        cmd = ['psql', '-c', command]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running command: {' '.join(cmd)}")
            print(f"Error: {result.stderr}")
            return None
        return result.stdout
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def check_postgres_running():
    """Check if PostgreSQL server is running."""
    print("Checking PostgreSQL status...")
    try:
        result = subprocess.run(['sudo', 'service', 'postgresql', 'status'], 
                               capture_output=True, text=True)
        
        if "online" in result.stdout:
            print("✅ PostgreSQL is running")
            return True
        else:
            print("❌ PostgreSQL is not running")
            try:
                print("Starting PostgreSQL...")
                subprocess.run(['sudo', 'service', 'postgresql', 'start'], check=True)
                print("✅ PostgreSQL started successfully")
                return True
            except Exception as e:
                print(f"❌ Failed to start PostgreSQL: {str(e)}")
                return False
    except Exception as e:
        print(f"❌ Error checking PostgreSQL status: {str(e)}")
        return False

def check_parse_db_uri():
    """Check and parse the database URI."""
    database_uri = os.environ.get('DATABASE_URI')
    if not database_uri:
        print("❌ DATABASE_URI environment variable not found")
        return None
    
    # print(f"Found DATABASE_URI: {database_uri}")
    
    if not database_uri.startswith('postgresql://'):
        print("❌ DATABASE_URI must start with 'postgresql://'")
        return None
    
    try:
        # Parse the connection string
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
        
        print(f"Parsed connection: postgresql://{username}:{'*' * len(password)}@{host}:{port}/{dbname}")
            
        return {
            'username': username,
            'password': password,
            'host': host,
            'port': port,
            'dbname': dbname
        }
    except Exception as e:
        print(f"❌ Error parsing DATABASE_URI: {str(e)}")
        return None

def check_user_exists(username):
    """Check if PostgreSQL user exists."""
    print(f"Checking if user '{username}' exists...")
    result = run_psql_command(f"SELECT usename FROM pg_user WHERE usename='{username}';")
    
    if result and username in result:
        print(f"✅ User '{username}' exists")
        return True
    else:
        print(f"❌ User '{username}' does not exist")
        return False

def create_user(username, password=None):
    """Create PostgreSQL user."""
    print(f"Creating user '{username}'...")
    
    if password is None:
        password = getpass.getpass(f"Enter password for new PostgreSQL user '{username}': ")
    
    # Create the user with password
    result = run_psql_command(f"CREATE USER {username} WITH ENCRYPTED PASSWORD '{password}';")
    
    if result is not None:
        print(f"✅ User '{username}' created successfully")
        return True
    else:
        print(f"❌ Failed to create user '{username}'")
        return False

def check_database_exists(dbname):
    """Check if database exists."""
    print(f"Checking if database '{dbname}' exists...")
    result = run_psql_command(f"SELECT datname FROM pg_database WHERE datname='{dbname}';")
    
    if result and dbname in result:
        print(f"✅ Database '{dbname}' exists")
        return True
    else:
        print(f"❌ Database '{dbname}' does not exist")
        return False

def create_database(dbname, owner):
    """Create PostgreSQL database."""
    print(f"Creating database '{dbname}' with owner '{owner}'...")
    result = run_psql_command(f"CREATE DATABASE {dbname} OWNER {owner};")
    
    if result is not None:
        print(f"✅ Database '{dbname}' created successfully")
        return True
    else:
        print(f"❌ Failed to create database '{dbname}'")
        return False

def grant_privileges(username, dbname):
    """Grant privileges on database to user."""
    print(f"Granting privileges on '{dbname}' to '{username}'...")
    result = run_psql_command(f"GRANT ALL PRIVILEGES ON DATABASE {dbname} TO {username};")
    
    if result is not None:
        print(f"✅ Privileges granted successfully")
        return True
    else:
        print(f"❌ Failed to grant privileges")
        return False

def initialize_database():
    """Initialize the database for the Budget App."""
    print("===== Budget App Database Initialization =====\n")
    
    # Check if PostgreSQL is running
    if not check_postgres_running():
        return False
    
    # Parse DATABASE_URI
    db_info = check_parse_db_uri()
    if not db_info:
        return False
    
    username = db_info['username']
    password = db_info['password']
    dbname = db_info['dbname']
    
    # Check/create user
    if not check_user_exists(username):
        if not create_user(username, password):
            return False
    
    # Check/create database
    if not check_database_exists(dbname):
        if not create_database(dbname, username):
            return False
        
    # Grant privileges
    if not grant_privileges(username, dbname):
        return False
    
    print("\n===== Database initialization completed successfully =====")
    print("You can now run 'flask init-db' to create the tables.")
    return True

if __name__ == "__main__":
    if initialize_database():
        sys.exit(0)
    else:
        print("\nDatabase initialization failed. Please check the error messages above.")
        sys.exit(1)
