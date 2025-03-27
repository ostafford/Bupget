# Database Schema Documentation

This document provides detailed information about the database schema used in the Budget App.

## Overview

The database schema consists of several interconnected tables that store financial data, user information, and forecasting data. The schema is designed to:

1. Track financial transactions with proper categorization
2. Monitor account balances over time
3. Store recurring expense information with version history
4. Calculate weekly summaries and future projections
5. Support the calendar-based view with appropriate data structures

## Entity Relationship Diagram

```
+-------------+       +---------------+       +----------------+
|    User     |------>|    Account    |------>| AccountBalance |
+-------------+       +---------------+       |    History     |
      |                     |                 +----------------+
      |                     |
      |                     |                 +----------------+
      |                     +---------------->|  Transaction   |
      |                     |                 +----------------+
      |                     |                       |
      |                     |                       |
      |                     |                       v
      |                     |                 +----------------+
      +-------------------->|                 | Transaction    |
      |                     |                 |   Category     |
      |                     |                 +----------------+
      |                     |
      |                     |                 +----------------+
      +-------------------->|                 | WeeklySummary  |
      |                     |                 +----------------+
      |                     |
      |                     |                 +----------------+
      +-------------------->|                 | RecurringExp.  |
      |                     |                 +----------------+
      |                     |                       |
      |                     |                       v
      |                     |                 +----------------+
      |                     |                 | RecurringExp.  |
      |                     |                 |    History     |
      |                     |                 +----------------+
      |                     |
      |                     |                 +----------------+
      +-------------------->|                 | TargetDate     |
                            |                 |   Forecast     |
                            |                 +----------------+
                            |
                            |                 +----------------+
                            +---------------->| MonthlyForecast|
                                              +----------------+
```

## Table Descriptions

### User

Stores user authentication and profile information.

| Column        | Type          | Description                           |
|---------------|---------------|---------------------------------------|
| id            | Integer (PK)  | Primary key                           |
| email         | String        | User email address (unique)           |
| password_hash | String        | Securely hashed password              |
| first_name    | String        | User's first name                     |
| last_name     | String        | User's last name                      |
| up_bank_token | String        | Up Bank API token (encrypted)         |
| preferences   | JSON          | User preferences                      |
| created_at    | DateTime      | When the user was created             |
| last_login    | DateTime      | When user last logged in              |

### Account

Represents financial accounts like bank accounts and credit cards.

| Column                | Type          | Description                           |
|-----------------------|---------------|---------------------------------------|
| id                    | Integer (PK)  | Primary key                           |
| external_id          | String        | ID from external source (e.g., Up Bank) |
| name                  | String        | Account name                          |
| type                  | Enum          | Account type (checking, savings, etc.) |
| source                | Enum          | Data source (MANUAL, UP_BANK)         |
| balance               | Numeric       | Current balance                       |
| currency              | String        | Currency code (e.g., AUD)             |
| credit_limit          | Numeric       | Credit limit (for credit cards)       |
| interest_rate         | Numeric       | Annual interest rate                  |
| payment_due_date      | Date          | Next payment due date                 |
| minimum_payment       | Numeric       | Minimum payment required              |
| user_id               | Integer (FK)  | Reference to User                     |
| created_at            | DateTime      | When the account was created          |
| updated_at            | DateTime      | When the account was last updated     |
| last_synced           | DateTime      | When data was last synced             |
| notes                 | Text          | Optional notes                        |
| is_active             | Boolean       | Whether account is active             |
| include_in_calculations | Boolean     | Whether to include in calculations    |

### AccountBalanceHistory

Tracks account balance changes over time.

| Column         | Type          | Description                           |
|----------------|---------------|---------------------------------------|
| id             | Integer (PK)  | Primary key                           |
| account_id     | Integer (FK)  | Reference to Account                  |
| date           | Date          | Date of this balance snapshot         |
| balance        | Numeric       | Account balance on this date          |
| transaction_id | Integer (FK)  | Optional reference to Transaction     |

### Transaction

Stores individual financial transactions.

| Column          | Type          | Description                           |
|-----------------|---------------|---------------------------------------|
| id              | Integer (PK)  | Primary key                           |
| external_id     | String        | ID from external source               |
| date            | Date          | Transaction date                      |
| amount          | Numeric       | Transaction amount                    |
| description     | String        | Transaction description               |
| is_extra        | Boolean       | Whether this is an "extra" transaction |
| source          | Enum          | Transaction source (MANUAL, UP_BANK, etc.) |
| recurring_expense_id | Integer (FK) | Optional reference to RecurringExpense |
| category_id     | Integer (FK)  | Optional reference to TransactionCategory |
| user_id         | Integer (FK)  | Reference to User                     |
| created_at      | DateTime      | When the transaction was created      |
| updated_at      | DateTime      | When the transaction was last updated |
| notes           | Text          | Optional notes                        |
| account_id      | Integer (FK)  | Reference to Account                  |

### TransactionCategory

Allows categorizing transactions for reporting and analysis.

| Column          | Type          | Description                           |
|-----------------|---------------|---------------------------------------|
| id              | Integer (PK)  | Primary key                           |
| name            | String        | Category name                         |
| color           | String        | Optional color code for display       |
| icon            | String        | Optional icon name                    |
| user_id         | Integer (FK)  | Reference to User                     |

### WeeklySummary

Stores financial summaries for each week.

| Column          | Type          | Description                           |
|-----------------|---------------|---------------------------------------|
| id              | Integer (PK)  | Primary key                           |
| week_start_date | Date          | Monday of this week                   |
| user_id         | Integer (FK)  | Reference to User                     |
| total_amount    | Numeric       | Total amount for the week             |
| total_expenses  | Numeric       | Total expenses for the week           |
| total_income    | Numeric       | Total income for the week             |
| total_extras    | Numeric       | Total "extras" for the week           |
| category_totals | JSON          | Category-specific totals              |
| calculated_at   | DateTime      | When this summary was calculated      |

### RecurringExpense

Represents regular expenses that occur on a schedule.

| Column          | Type          | Description                           |
|-----------------|---------------|---------------------------------------|
| id              | Integer (PK)  | Primary key                           |
| name            | String        | Expense name                          |
| amount          | Numeric       | Expense amount                        |
| frequency       | Enum          | Frequency (weekly, monthly, etc.)     |
| next_date       | Date          | Next occurrence date                  |
| start_date      | Date          | When this expense starts              |
| end_date        | Date          | Optional end date                     |
| is_active       | Boolean       | Whether this expense is active        |
| created_at      | DateTime      | When this expense was created         |
| notes           | Text          | Optional notes                        |
| user_id         | Integer (FK)  | Reference to User                     |

### RecurringExpenseHistory

Tracks changes to recurring expenses over time.

| Column           | Type          | Description                           |
|------------------|---------------|---------------------------------------|
| id               | Integer (PK)  | Primary key                           |
| current_expense_id | Integer (FK) | Reference to RecurringExpense         |
| name             | String        | Expense name at this point in history |
| amount           | Numeric       | Expense amount at this point          |
| frequency        | Enum          | Frequency at this point               |
| effective_date   | DateTime      | When this version was effective       |

### TargetDateForecast

Represents budget projections for specific target dates.

| Column                   | Type          | Description                           |
|--------------------------|---------------|---------------------------------------|
| id                       | Integer (PK)  | Primary key                           |
| name                     | String        | Forecast name (e.g., "End of June 25") |
| target_date              | Date          | The date to project for               |
| user_id                  | Integer (FK)  | Reference to User                     |
| projected_balance        | Numeric       | Projected balance at target date      |
| created_at               | DateTime      | When forecast was created             |
| last_calculated          | DateTime      | When forecast was last calculated     |
| calculation_details      | JSON          | Details of the calculation            |
| recurring_expenses_snapshot | JSON       | Snapshot of expenses used             |
| notes                    | Text          | Optional notes                        |

### MonthlyForecast

Represents budget projections for specific months.

| Column                | Type          | Description                           |
|-----------------------|---------------|---------------------------------------|
| id                    | Integer (PK)  | Primary key                           |
| year                  | Integer       | Year for this forecast                |
| month                 | Integer       | Month for this forecast (1-12)        |
| user_id               | Integer (FK)  | Reference to User                     |
| starting_balance      | Numeric       | Balance at start of month             |
| projected_income      | Numeric       | Projected income for month            |
| projected_expenses    | Numeric       | Projected expenses for month          |
| projected_end_balance | Numeric       | Projected balance at end of month     |
| credit_card_projections | JSON        | Credit card specific projections      |
| created_at            | DateTime      | When forecast was created             |
| last_calculated       | DateTime      | When forecast was last calculated     |

## Database Relationships

### One-to-Many Relationships

- User → Accounts: One user can have many accounts
- User → Transactions: One user can have many transactions
- User → RecurringExpenses: One user can have many recurring expenses
- User → WeeklySummaries: One user can have many weekly summaries
- User → TransactionCategories: One user can have many transaction categories
- User → TargetDateForecasts: One user can have many target date forecasts
- User → MonthlyForecasts: One user can have many monthly forecasts
- Account → Transactions: One account can have many transactions
- Account → AccountBalanceHistory: One account can have many balance history records
- TransactionCategory → Transactions: One category can apply to many transactions
- RecurringExpense → RecurringExpenseHistory: One recurring expense can have many history records

## Data Flow

1. **Transaction Data Flow**:
   - Transactions are created either manually or imported from Up Bank
   - Each transaction is assigned to an account and optionally a category
   - Transactions affect account balances
   - Transactions are grouped into weekly summaries

2. **Recurring Expense Flow**:
   - Recurring expenses are defined with a frequency and amount
   - When an expense amount changes, a history record is created
   - Future projections use the appropriate expense amount based on the date

3. **Forecasting Flow**:
   - Forecasts combine current account balances, future transactions, and recurring expenses
   - Target date forecasts project balances for specific future dates
   - Monthly forecasts provide month-by-month projections

## Special Considerations

### Version History

The schema includes version history for recurring expenses, allowing for accurate projections when expense amounts change.

### Currency Handling

All monetary amounts are stored as Numeric(10, 2) to ensure precise decimal calculations without floating-point errors.

### Date Management

The database uses these date-related concepts:
- Transaction date: When the transaction occurred
- Week start date: Monday of each week for weekly summaries
- Next date: When a recurring expense will next occur
- Target date: A future date to project a budget for

### Enumerations

The schema uses several enumerations to restrict values:
- AccountType: CHECKING, SAVINGS, CREDIT_CARD, LOAN, INVESTMENT
- AccountSource: MANUAL, UP_BANK
- TransactionSource: MANUAL, UP_BANK, RECURRING
- FrequencyType: WEEKLY, FORTNIGHTLY, MONTHLY, QUARTERLY, YEARLY
