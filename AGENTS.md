# AGENTS.md

## Dependency Injection (DI)

The application uses `dependency-injector` for dependency injection to achieve loose coupling and better testability.

### Container Setup
- **Location**: `HOTEL/container.py`
- **Initialization**: `HOTEL/__init__.py` (lazy-loaded to avoid Django setup issues)
- **Access**: `from HOTEL import get_container; container = get_container()`

### Current Services

#### Clients Module
```python
# Infrastructure (Singletons)
container.client_repo          # ClientRepository
container.password_manager     # DjangoPasswordManager
container.session_manager      # DjangoSessionManager
container.captcha_service      # GoogleRecaptchaV3Verifier

# Application (Factories)
container.client_service()     # ClientService instance
```

#### Reservations Module
```python
# Infrastructure (Singletons)
container.reservation_repo     # ReservationRepository
container.room_repo            # RoomRepository
container.unit_of_work         # UnitOfWork

# Application (Factories)
container.reservation_service() # ReservationService instance
```

#### Payments Module
```python
# Infrastructure (Singletons)
container.payment_repo         # PaymentRepository
container.payment_gateway      # StripeCheckoutSession
container.webhook_handler      # StripePaymentWebhookHandler
container.task_queuer          # DjangoQTaskQueuer
container.email_sender         # DjangoEmailSender
container.pdf_generator        # ReportLabPDFReceiptGenerator
container.logger               # Python Logger

# Use Cases (Singletons)
container.confirmation_usecase # SendPaymentConfirmationUseCase
container.activate_reservation_usecase # ActivateReservationUseCase
container.schedule_reservation_usecase # ScheduleReservationUseCase
container.release_reservation_usecase # ReleaseReservationUseCase

# Application (Factories)
container.payment_service()    # PaymentService instance
```

### Usage in Views
```python
from HOTEL import get_container

def setup(self, request, *args, **kwargs):
    self.svc = get_container().client_service()
```

### Adding New Dependencies
1. **Infrastructure**: Add to `Container` as `providers.Singleton()`
2. **Services**: Add to `Container` as `providers.Factory()`
3. **Views**: Use `get_container().new_service()` in view setup

### Testing with DI
Tests automatically use the container. Override dependencies by mocking the container providers.

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
