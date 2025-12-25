# AGENTS.md

## Build/Lint/Test Commands
- `poetry run task run` - Start Django development server
- `poetry run python manage.py migrate` - Run database migrations
- `poetry run task test` - Run all tests
- `poetry run pytest tests/unit/path/to/test_file.py::test_function_name` - Run single test
- `poetry run task lint` - Lint code (Ruff)
- `poetry run task format` - Format code (Ruff)
- `poetry run task typecheck` - Typecheck code (MyPy)
- `poetry run task scan` - Scan for vulnerabilities (Bandit)

## Code Style Guidelines
- **Language**: Python 3.9+ with Django 3.2, Poetry for dependencies
- **Architecture**: Domain-driven design (domain/, application/, infra/ layers)
- **Formatting**: 95 char lines, single quotes, 4-space indentation, Ruff (preview mode)
- **Imports**: Standard → Django → Local (grouped by module)
- **Naming**: snake_case vars/functions, PascalCase classes, UPPER_SNAKE_CASE constants
- **Types**: Full type hints with `typing` module
- **Error Handling**: Result pattern, Django ValidationError, custom messages in feedback_messages.py
- **Documentation**: Portuguese docstrings, English comments, descriptive variable names
- **Architecture**: Domain entities, application services, infra adapters, repository pattern, CQRS-style separation
