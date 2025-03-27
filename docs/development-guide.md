# Development Guide

This guide provides information for developers working on the Budget App project.

## Development Environment Setup

### Setting Up Your Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/budget-app.git
   cd budget-app
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

5. Create a `.env` file with your development configuration:
   ```
   FLASK_CONFIG=development
   FLASK_DEBUG=1
   SECRET_KEY=your-development-secret-key
   DATABASE_URI=postgresql://postgres:password@localhost/budget_app
   UP_BANK_API_TOKEN=your-up-bank-token
   ```

6. Initialize the database:
   ```bash
   flask init-db
   ```

7. Create a demo user:
   ```bash
   flask create-demo-user
   ```

8. Run the application:
   ```bash
   flask run
   ```

### Using Docker for Development

If you prefer to use Docker:

1. Make sure Docker and Docker Compose are installed.

2. Build and start the containers:
   ```bash
   docker-compose up -d
   ```

3. Access the application at http://localhost:5000

## Project Structure

The Budget App follows a modular structure:

- **Flask Application Factory**: The application is created using the factory pattern in `app/__init__.py`.
- **Blueprints**: Routes are organized into blueprints (e.g., `auth`, `dashboard`, `calendar`).
- **Models**: Database models are in the `app/models/` directory.
- **Services**: Business logic is separated into service modules in `app/services/`.
- **API Integration**: External API integration is in the `app/api/` directory.
- **Templates**: HTML templates are in the `app/templates/` directory.
- **Static Files**: CSS, JavaScript, and images are in the `app/static/` directory.
- **Commands**: CLI commands are defined in `app/commands.py`.

## Development Workflow

### Git Workflow

We use a simple Git workflow:

1. Create a new branch for each feature or bug fix:
   ```bash
   git checkout -b feature/feature-name
   ```

2. Make your changes and commit them with descriptive messages:
   ```bash
   git add .
   git commit -m "Add feature X"
   ```

3. Push your branch to the remote repository:
   ```bash
   git push origin feature/feature-name
   ```

4. Create a pull request for review.

### Database Migrations

When making changes to database models:

1. Update the model definition in the appropriate file in `app/models/`.

2. Generate a migration:
   ```bash
   flask db migrate -m "Description of the changes"
   ```

3. Review the generated migration script in the `migrations/versions/` directory.

4. Apply the migration:
   ```bash
   flask db upgrade
   ```

### Adding New Features

When adding new features, follow these steps:

1. **Create or update models**: Define the data structures needed.
2. **Add service functions**: Implement the business logic.
3. **Create or update routes**: Add endpoints to expose the functionality.
4. **Add templates or API responses**: Create the user interface.
5. **Add tests**: Write tests for your feature.
6. **Update documentation**: Document your changes.

## Coding Standards

### Python Style Guide

We follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for Python code. Key points:

- Use 4 spaces for indentation
- Maximum line length of 88 characters
- Use descriptive variable and function names
- Add docstrings to all functions, classes, and modules

### JavaScript Style Guide

For JavaScript, we follow the [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript). Key points:

- Use camelCase for variables and functions
- Use PascalCase for classes and components
- Use semicolons
- Prefer ES6 features (arrow functions, destructuring, etc.)

### Commenting

Every function, class, and module should have a docstring that explains:
- What it does
- Parameters and their types
- Return values and their types
- Any exceptions that might be raised

Example:
```python
def calculate_weekly_summary(user_id, week_start_date):
    """
    Calculate a weekly summary for a user.
    
    Args:
        user_id (int): The user ID
        week_start_date (date): Monday of the week to calculate
        
    Returns:
        WeeklySummary: The calculated weekly summary
        
    Raises:
        ValueError: If week_start_date is not a Monday
    """
    # Implementation here
```

Additionally, include comments for complex logic explaining why a particular approach was chosen.

## Testing

### Running Tests

Run the full test suite:
```bash
pytest
```

Run specific tests:
```bash
pytest tests/test_api.py
```

Run tests with coverage report:
```bash
pytest --cov=app tests/
```

### Writing Tests

Tests are organized in the `tests/` directory, mirroring the structure of the `app/` directory.

Each test file should focus on a specific component:
- `test_models.py`: Tests for database models
- `test_api.py`: Tests for API endpoints
- `test_services.py`: Tests for service functions

Test functions should follow this naming convention:
```python
def test_function_name_condition_being_tested():
    # Test implementation
```

Example:
```python
def test_weekly_summary_calculation_with_no_transactions():
    # Test code here
```

## Deployment

### Production Setup

For production deployment:

1. Set secure environment variables:
   ```
   FLASK_CONFIG=production
   SECRET_KEY=a-secure-random-key
   DATABASE_URI=postgresql://user:password@host/dbname
   ```

2. Use a production WSGI server like Gunicorn:
   ```bash
   pip install gunicorn
   gunicorn "app:create_app()"
   ```

3. Set up a reverse proxy like Nginx to handle static files and SSL termination.

### Continuous Integration/Deployment

We use GitHub Actions for CI/CD. The workflow includes:

1. Running tests
2. Checking code style
3. Generating coverage reports
4. Deploying to staging/production environments

## Troubleshooting

### Common Development Issues

1. **Database migration conflicts**:
   - If you encounter migration conflicts, try resetting the database:
     ```bash
     flask drop-db
     flask init-db
     ```

2. **Template not found errors**:
   - Check that the template path is correct
   - Verify that the blueprint has the correct template folder

3. **Static files not loading**:
   - Check browser console for path errors
   - Verify that static files are in the correct location

4. **SQLAlchemy errors**:
   - Use `db.session.rollback()` to recover from transaction errors
   - Check model relationships and foreign key constraints

### Debugging Tips

1. Use Flask's debug mode to get detailed error pages:
   ```
   FLASK_DEBUG=1
   ```

2. Add print statements or use logging:
   ```python
   current_app.logger.debug("Variable value: %s", variable)
   ```

3. Use an interactive debugger:
   ```python
   import pdb; pdb.set_trace()
   ```

4. Check the application logs:
   ```bash
   tail -f logs/application.log
   ```

## Adding New Dependencies

When adding new dependencies:

1. Install the package:
   ```bash
   pip install package-name
   ```

2. Add it to requirements.txt:
   ```bash
   pip freeze > requirements.txt
   ```

3. Document why the dependency was added in the commit message.

## Security Considerations

### Handling Sensitive Data

- Never commit secrets or credentials to version control
- Use environment variables for sensitive configuration
- Encrypt sensitive data stored in the database
- Use HTTPS for all communication

### Authentication and Authorization

- User passwords are hashed using Werkzeug's security functions
- API tokens (like Up Bank tokens) are stored securely
- Access control is enforced at the route level with Flask-Login
- CSRF protection is enabled for all forms

### Input Validation

- Validate all user input
- Use request parsers and form validators
- Escape output to prevent XSS attacks
- Use prepared statements for database queries

## Performance Optimization

### Database Query Optimization

- Use appropriate indexes on frequently queried columns
- Limit the number of database queries per request
- Use eager loading for relationships that are always needed
- Paginate large result sets

### Caching

- Use Flask-Caching for caching responses
- Cache expensive calculations
- Implement ETag and conditional requests for API responses

## Contributing

New contributors should:

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Run tests
5. Submit a pull request

All contributions should include appropriate tests and documentation updates.
