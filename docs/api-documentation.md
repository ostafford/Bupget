# API Documentation

This document describes the API endpoints available in the Budget App.

## Authentication

All API endpoints (except webhooks) require authentication. The application uses cookie-based authentication with Flask-Login.

## Up Bank Integration

### Connect to Up Bank

**Endpoint:** `/api/up-bank/connect`
**Method:** POST
**Authentication:** Required

Connects a user account to Up Bank using a personal access token.

**Request Body:**
```json
{
  "token": "up:yeah:your-personal-access-token"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully connected to Up Bank"
}
```

### Sync Up Bank Data

**Endpoint:** `/api/up-bank/sync`
**Method:** POST
**Authentication:** Required

Syncs account and transaction data from Up Bank.

**Request Body:**
```json
{
  "days_back": 30
}
```

**Response:**
```json
{
  "success": true,
  "message": "Synced 10 new and 5 existing transactions",
  "transaction_count": 15
}
```

### Up Bank Webhook

**Endpoint:** `/api/up-bank/webhook`
**Method:** POST
**Authentication:** Not required (uses Up Bank signature verification)

Receives real-time updates from Up Bank.

**Request Body:** Webhook payload from Up Bank
**Response:** 200 OK

## Calendar API

### Get Weekly Data

**Endpoint:** `/calendar/api/weeks`
**Method:** GET
**Authentication:** Required

Retrieves transaction data grouped by week for the calendar view.

**Query Parameters:**
- `start` (optional): ISO date string for the starting date
- `weeks` (optional): Number of weeks to retrieve (default: 4)

**Response:**
```json
{
  "2023-01-02": {
    "start_date": "2023-01-02",
    "end_date": "2023-01-08",
    "days": {
      "2023-01-02": [
        {
          "id": 1,
          "description": "Grocery shopping",
          "amount": -85.75,
          "is_extra": false,
          "category_id": 1,
          "source": "UP_BANK"
        }
      ],
      "2023-01-03": []
    },
    "summary": {
      "total_amount": -120.50,
      "total_expenses": -150.75,
      "total_income": 30.25,
      "total_extras": -35.00
    }
  }
}
```

### Get Recurring Expenses

**Endpoint:** `/calendar/api/recurring`
**Method:** GET
**Authentication:** Required

Retrieves active recurring expenses for the current user.

**Response:**
```json
[
  {
    "id": 1,
    "name": "Netflix",
    "amount": 15.99,
    "frequency": "MONTHLY",
    "next_date": "2023-02-15"
  }
]
```

### Get Transaction Details

**Endpoint:** `/calendar/api/transaction/{transaction_id}`
**Method:** GET
**Authentication:** Required

Retrieves details for a specific transaction.

**Response:**
```json
{
  "id": 1,
  "date": "2023-01-02",
  "description": "Grocery shopping",
  "amount": -85.75,
  "is_extra": false,
  "category_id": 1,
  "source": "UP_BANK",
  "notes": "Weekly groceries",
  "created_at": "2023-01-02T15:30:45",
  "updated_at": "2023-01-02T15:30:45"
}
```

### Create Transaction

**Endpoint:** `/calendar/api/transaction`
**Method:** POST
**Authentication:** Required

Creates a new transaction.

**Request Body:**
```json
{
  "date": "2023-01-10",
  "amount": -25.50,
  "description": "Lunch",
  "is_extra": true,
  "category_id": 3,
  "notes": "Business lunch",
  "account_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "transaction": {
    "id": 10,
    "date": "2023-01-10",
    "description": "Lunch",
    "amount": -25.50
  }
}
```

### Update Transaction

**Endpoint:** `/calendar/api/transaction/{transaction_id}`
**Method:** PUT
**Authentication:** Required

Updates an existing transaction.

**Request Body:**
```json
{
  "amount": -30.75,
  "description": "Lunch with client"
}
```

**Response:**
```json
{
  "success": true,
  "transaction": {
    "id": 10,
    "date": "2023-01-10",
    "description": "Lunch with client",
    "amount": -30.75
  }
}
```

### Delete Transaction

**Endpoint:** `/calendar/api/transaction/{transaction_id}`
**Method:** DELETE
**Authentication:** Required

Deletes a transaction.

**Response:**
```json
{
  "success": true
}
```

## Error Responses

All API endpoints return appropriate HTTP status codes:

- 200: Success
- 400: Bad request (invalid parameters)
- 401: Unauthorized (not authenticated)
- 403: Forbidden (authenticated but not authorized)
- 404: Not found (resource doesn't exist)
- 500: Server error

Error responses have this structure:

```json
{
  "error": "Error message describing what went wrong"
}
```

## Rate Limiting

API endpoints have a rate limit of 100 requests per minute per user.

## Webhooks

The application provides a webhook endpoint for Up Bank to send real-time transaction updates.

### Security

The webhook endpoint verifies the signature of incoming requests using the Up Bank webhook secret.

### Payload

The webhook payload follows the Up Bank webhook format. The application specifically processes these event types:

- `TRANSACTION_CREATED`
- `TRANSACTION_SETTLED`
- `TRANSACTION_DELETED`

### Processing

When a webhook is received:
1. The signature is verified
2. The event type is determined
3. The appropriate action is taken (creating/updating/deleting a transaction)
4. Weekly summaries affected by the transaction are recalculated
