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

```
budget_app/
│
├── app/                        # Application package
│   ├── __init__.py            # Flask application factory
│   ├── config.py              # Configuration settings
│   ├── extensions.py          # Flask extensions initialization
│   ├── commands.py            # CLI commands
│   │
│   ├── models/                # Database models
│   │   ├── __init__.py
│   │   ├── user.py            # User model
│   │   ├── account.py         # Bank account model
│   │   ├── transaction.py     # Transaction model
│   │   ├── recurring.py       # Recurring expense model
│   │   └── forecast.py        # Forecast models
│   │
│   ├── api/                   # API integration
│   │   ├── __init__.py
│   │   └── up_bank.py         # Up Bank API connector
│   │
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   └── bank_service.py    # Banking service functions
│   │
│   ├── routes/                # Route definitions
│   │   ├── __init__.py
│   │   ├── main.py            # Main routes
│   │   ├── auth.py            # Authentication routes
│   │   ├── dashboard.py       # Dashboard routes
│   │   ├── transactions.py    # Transaction management
│   │   ├── budget.py          # Budget management
│   │   ├── up_bank.py         # Up Bank integration
│   │   ├── calendar.py        # Calendar view
│   │   └── api.py             # API endpoints
│   │
│   ├── static/                # Static assets
│   │   ├── css/
│   │   ├── js/
│   │   └── img/
│   │
│   └── templates/             # HTML templates
│
├── migrations/                # Database migration files
│
├── tests/                     # Test suite
│
├── .env                       # Environment variables (not in git)
├── .env.example               # Example environment variables
├── .gitignore                 # Git ignore file
├── requirements.txt           # Python dependencies
└── run.py                     # Application entry point
```

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- PostgreSQL
- Up Bank account (for API access)

### Up Bank API Integration

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

Run tests with:
```bash
pytest
```

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

## Future Enhancements

Planned features for future development:

1. Enhanced calendar visualization with category coloring
2. More detailed forecasting models
3. Budget vs. actual comparisons
4. Mobile-responsive design

## License

This project is licensed under the MIT License - see the LICENSE file for details.
