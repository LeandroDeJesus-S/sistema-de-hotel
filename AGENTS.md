# AGENTS.md

## Build/Lint/Test Commands

### Development Server
- `poetry run task run` - Start Django development server
- `poetry run python manage.py migrate` - Run database migrations
- `poetry run python manage.py check` - Validate Django configuration

### Testing
- `poetry run task test` - Run all tests
- `poetry run pytest tests/unit/path/to/test_file.py::test_function_name` - Run single test
- `poetry run pytest tests/unit/clients/models/test_client_model.py::test_client_model_creation_with_valid_data` - Example single test

### Code Quality
- `poetry run task lint` - Lint code
- `poetry run task format` - Format code
- `poetry run task typecheck` - Typecheck code
- `poetry run task scan` - Scan for vulnerabilities

## Code Style Guidelines

### Language & Framework
- Python 3.9+ with Django 3.2
- Domain-driven design: domain/, application/, infra/ layers
- Poetry for dependency management

### Formatting & Linting
- Line length: 95 characters
- Single quotes for strings
- 4-space indentation
- Ruff for linting/formatting (preview mode enabled)
- Pre-commit hooks enforce code quality

### Imports
```python
# Standard library
import logging
from typing import Any

# Django imports
from django.conf import settings
from django.contrib import messages

# Local imports (grouped by module)
from clients.application.dtos import ChangePasswordInput
from clients.models import Client
```

### Naming Conventions
- Variables/functions: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE
- Methods: descriptive verbs (create_user, validate_data)

### Type Hints
```python
def process_payment(self, amount: float, currency: str = 'BRL') -> dict[str, Any]:
    # Function implementation
    pass
```

### Error Handling
- Use Result pattern: `result.is_err()` / `result.unwrap_err()`
- Django ValidationError for model validation
- Custom error messages in feedback_messages.py

### Documentation
- Portuguese docstrings for user-facing text
- English comments for technical implementation
- Descriptive variable names reduce comment needs

### Architecture Patterns
- Domain entities with business logic
- Application services coordinate operations
- Infrastructure adapters handle external dependencies
- Repository pattern for data access
- CQRS-style separation in some modules
