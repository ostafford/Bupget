# Budget App

A web application that extends the functionality of a Google Sheets budgeting system with real-time transaction data from Up Bank, calendar-based visualization, and future budget projections.

## Project Overview

This application allows users to:
- Connect to the Up Bank API to retrieve real-time transaction data
- View transactions in a weekly calendar format (similar to the original spreadsheet)
- Track recurring expenses with proper version history
- Generate future budget projections for specific target dates
- Calculate weekly and monthly financial summaries

## Technology Stack

- **Backend**: Python 3.8+ with Flask framework
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Authentication**: Flask-Login
- **API Integration**: Up Bank API

## Project Structure

The Budget App follows a modular structure:

- **Flask Application Factory**: The application is created using the factory pattern in `app/__init__.py`.
- **Blueprints**: Routes are organized into logical blueprints:
  - `main.py`: Main pages (home, about)
  - `auth.py`: Authentication (login, registration)
  - `dashboard.py`: User dashboard 
  - `calendar.py`: Calendar view and API endpoints
  - `transactions.py`: Transaction management
  - `budget.py`: Budget management
  - `upbank.py`: Up Bank integration (both UI views and API endpoints)
- **Models**: Database models in the `app/models/` directory.
- **Services**: Business logic in the `app/services/` directory, organized by domain:
  - `auth_service.py`: Authentication functions
  - `bank_service.py`: Banking operations
  - `transaction_service.py`: Transaction processing
  - `budget_service.py`: Budget calculations
  - `forecast_service.py`: Financial forecasting
- **API Integration**: External API integration in the `app/api/` directory:
  - `up_bank.py`: Up Bank API client
  - `webhooks.py`: Webhook handling for real-time updates
  - `error_handling.py`: Shared error handling utilities
- **Templates**: HTML templates in the `app/templates/` directory.
- **Static Files**: CSS, JavaScript, and images in the `app/static/` directory:
  - JavaScript is organized with shared utilities in `utils.js`
- **Commands**: CLI commands in the `app/commands/` directory, organized by function.

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- PostgreSQL
- Up Bank account (for API access)

### Up Bank API Integration
`
To connect to the Up Bank API:

1. Go to the [Up Bank developer portal](https://developer.up.com.au/) and create a personal access token.

2. Use the CLI command to connect your user to Up Bank:
   ```bash
   flask connect-up-bank <user_id> <your-up-bank-token>
   ```

3. Sync transactions from Up Bank:
   ```bash
   flask sync-up-bank <user_id>
   ```

## Database Models

### User Model

The User model represents application users and handles authentication.

Key fields:
- `id`: Primary key
- `email`: User email address
- `password_hash`: Securely hashed password
- `up_bank_token`: Stored token for Up Bank API access

### Account Model

The Account model represents bank accounts, including credit cards.

Key fields:
- `id`: Primary key
- `external_id`: ID from external source (e.g., Up Bank)
- `name`: Account name
- `type`: Account type (checking, savings, credit_card, etc.)
- `balance`: Current balance
- `currency`: Currency code
- `user_id`: Reference to user who owns the account

Credit card specific fields:
- `credit_limit`: Maximum credit limit
- `interest_rate`: Annual interest rate
- `payment_due_date`: Next payment due date

### Transaction Model

The Transaction model represents individual financial transactions.

Key fields:
- `id`: Primary key
- `external_id`: ID from external source (e.g., Up Bank)
- `date`: Transaction date
- `amount`: Transaction amount (negative for expenses)
- `description`: Transaction description
- `is_extra`: Flag for "extra" transactions
- `category_id`: Reference to transaction category
- `user_id`: Reference to user who owns the transaction
- `account_id`: Reference to account for this transaction

### RecurringExpense Model

The RecurringExpense model represents regular expenses that occur on a schedule.

Key fields:
- `id`: Primary key
- `name`: Expense name
- `amount`: Expense amount
- `frequency`: Frequency type (weekly, fortnightly, monthly, etc.)
- `next_date`: Next occurrence date
- `user_id`: Reference to user who owns this expense

### WeeklySummary Model

The WeeklySummary model represents financial summaries for each week.

Key fields:
- `id`: Primary key
- `week_start_date`: Monday of this week
- `total_amount`: Total amount for the week
- `total_expenses`: Total expenses for the week
- `total_income`: Total income for the week
- `total_extras`: Total "extras" for the week
- `user_id`: Reference to user who owns this summary

### TargetDateForecast Model

The TargetDateForecast model represents budget projections for specific target dates.

Key fields:
- `id`: Primary key
- `name`: Forecast name (e.g., "End of June 25")
- `target_date`: The date to project for
- `projected_balance`: Projected balance at target date
- `user_id`: Reference to user who owns this forecast

## CLI Commands

The application provides several CLI commands for management:

- `flask init-db`: Initialize the database and create tables
- `flask drop-db`: Drop all database tables (use with caution)
- `flask create-demo-user`: Create a demo user for testing
- `flask verify-setup`: Verify that the application setup is working correctly
- `flask connect-up-bank`: Connect a user to Up Bank
- `flask sync-up-bank`: Sync transactions from Up Bank

## API Endpoints

The application provides several API endpoints:

- `/api/up-bank/connect`: Connect to Up Bank API
- `/api/up-bank/sync`: Sync transactions from Up Bank
- `/api/up-bank/webhook`: Webhook endpoint for Up Bank real-time updates
- `/calendar/api/weeks`: Get transaction data for calendar weeks
- `/calendar/api/recurring`: Get recurring expenses for the calendar
- `/calendar/api/transaction`: CRUD operations for transactions

## Development Guidelines

### Code Style

This project follows the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for Python code.

### Testing

The project includes a comprehensive test suite in the `tests/` directory.

To run tests:
```bash
pytest

### Database Migrations

When making changes to the database models:

1. Generate a migration:
   ```bash
   flask db migrate -m "Description of changes"
   ```

2. Apply the migration:
   ```bash
   flask db upgrade
   ```

## Error Handling

The application uses a standardized approach to error handling, particularly for API integrations.

### API Error Handling

API errors are handled through the shared module `app/api/error_handling.py`, which provides:

1. **Exception Classes**:
   - `APIError`: Base exception for all API errors
   - `APIAuthError`: Authentication errors
   - `APIResponseError`: General response errors
   - `APIRateLimitError`: Rate limiting errors
   - `APIConnectionError`: Network and connection errors

2. **Retry Mechanism**:
   The `@retry` decorator provides automatic retries for operations that might fail transiently:
   ```python
   @retry(
       exceptions=[ConnectionError, Timeout, APIConnectionError],
       tries=3,
       delay=2,
       backoff=2
   )
   def some_function():
       # This will retry up to 3 times if it fails with the specified exceptions

### Python Style Guide

We follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for Python code with these specific patterns:

- **Services and Business Logic**: 
  - Business logic goes in the `app/services/` directory
  - Service functions should be stateless and focused on a specific domain
  - Database operations should be wrapped in try/except blocks with rollback

- **API Integration**:
  - External API clients go in the `app/api/` directory
  - Use the retry mechanism for operations that might fail transiently
  - Handle errors using the standardized error response format

- **Blueprints and Routes**:
  - Route functions should be thin, delegating business logic to services
  - Similar functionality should be grouped in the same blueprint
  - Separate view routes (returning HTML) from API routes (returning JSON)

### JavaScript Style Guide

For JavaScript, we follow these patterns:

- **Module Organization**:
  - Shared utilities go in `utils.js`
  - Page-specific functionality goes in dedicated files
  - Use DOM content loaded event to initialize scripts

- **API Communication**:
  - Use the `ApiUtils` module for all API requests
  - Handle errors consistently using try/catch
  - Show user-friendly messages for errors

- **UI Updates**:
  - Use the `UIUtils` module for common UI operations
  - Format dates and currency consistently
  - Separate data fetching from UI rendering logic

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify PostgreSQL is running
   - Check your DATABASE_URI in the .env file
   - Ensure you have the correct permissions

2. **Up Bank API Issues**
   - Confirm your token is valid and not expired
   - Check the API status at https://developer.up.com.au/

### Logging

The application logs are written to the console by default. Set the LOG_LEVEL in your .env file to control verbosity.

## Future Development Plans

### React Front-end Integration

The application is being prepared for a future migration to React for the front-end:

1. **Current State**: 
   - JavaScript code has been modularized with shared utilities
   - API communication is standardized with consistent patterns
   - UI rendering is separated from data fetching

2. **Migration Strategy**:
   - Start with small, self-contained components (e.g., transaction list)
   - Set up a proper build pipeline with Webpack
   - Incrementally convert each view to React components
   - Maintain API communication pattern through the ApiUtils module

3. **Benefits of React Migration**:
   - Improved UI reactivity and state management
   - Better component reusability
   - Enhanced user experience with smoother interactions
   - Easier testing of UI components

## License

This project is licensed under the MIT License - see the LICENSE file for details.
