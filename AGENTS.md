# Project Guidelines

This document contains the essential guidelines, architectural principles, and quality standards that MUST be followed for all development on the "Sistema de Hotel" project.

## 1. Core Philosophy

The primary goal is to build and maintain a clean, testable, and scalable application. This is achieved by strictly adhering to a layered architecture that separates business logic from infrastructure concerns.

## 2. Architectural Principles: Hexagonal (Ports & Adapters)

**Mandate:** All new features and modifications MUST follow the Hexagonal Architecture pattern as implemented in the `clients` app.

-   **Goal:** To isolate the core business logic (Domain and Application layers) from external details like the database, web framework, and third-party services.
-   **Refactoring:** When modifying existing code in apps like `payments` or `reservations` that do not yet fully adhere to this pattern, a refactoring effort should be made to align the modified feature with this architecture.

### Architectural Layers:

1.  **Domain Layer (`/domain`)**
    -   **Contents:** Business rules, entities, and value objects. It contains NO framework-specific code (i.e., no `import django`).
    -   **Entities (`entities.py`):** Pure data structures (Pydantic models or dataclasses) that represent core business concepts and contain validation logic.
    -   **Ports (`ports.py`):** Interfaces (`Protocol` or `ABC`) that define contracts for external services (e.g., `AbsClientRepository`, `AbsPasswordManager`).

2.  **Application Layer (`/application`)**
    -   **Contents:** Use cases that orchestrate the business logic.
    -   **Use Cases (`usecases.py`):** Classes that represent a single system action (e.g., `CreateUserUseCase`). They depend on Domain Ports, not concrete implementations.
    -   **DTOs (`dtos.py`):** Data Transfer Objects used to pass data to and from use cases, ensuring the application layer remains decoupled from web requests or other external inputs.

3.  **Infrastructure Layer (`/infra`)**
    -   **Contents:** Concrete implementations (Adapters) of the Domain Ports.
    -   **Adapters (`repo.py`, `adapters.py`):** Classes that interact with Django, databases, or external APIs (e.g., `ClientRepository` implements `AbsClientRepository` using the Django ORM).
    -   **Views (`views.py`):** Act as thin "Web Adapters". Their only job is to:
        1.  Receive an HTTP request.
        2.  Instantiate and call the appropriate Use Case with data from the request (via DTOs).
        3.  Translate the result from the Use Case into an HTTP response.

## 3. Testing Strategy

**Framework:** All tests MUST be written using `pytest` and its related plugins (`pytest-django`, `pytest-mock`).

-   **Unit Tests:**
    -   **Target:** Domain Entities and Application Use Cases.
    -   **Method:** Test these components in complete isolation. All external dependencies (Ports) MUST be mocked using `pytest-mock`.
-   **Integration Tests:**
    -   **Target:** Infrastructure Adapters (e.g., Repositories, Payment Gateways).
    -   **Method:** Test the adapter against a real (test) instance of the infrastructure it connects to. For repositories, this means using a test database.
-   **Location:** Tests should be placed in the `/tests` directory.
- Don't delete tests they should be kept for the sake of the project.
- Before starting to write a pytest fixture check whether or not it already exists in a outer `conftest.py` file to avoid duplicates.
- Fixtures cannot be defined in the same file as a test function, they must be set in `tests/unit/conftest.py` if it's globally shared or in its related app score (e.g.: `tests/unit/clients/conftest.py` for clients, `tests/unit/reservations/conftest.py` for reservations)
- `poetry run task test` - Run all tests with coverage
- `poetry run pytest tests/unit/path/to/test_file.py` - Run tests in specific directory
- `poetry run pytest tests/unit/path/to/test_file.py::TestClass::test_method` - Run single test method
- `poetry run pytest tests/unit/path/to/test_file.py::test_function_name` - Run single test function
- `poetry run pytest -k "test_name_pattern"` - Run tests matching pattern
- `poetry run pytest --cov=clients --cov-report=html` - Run tests with specific module coverage

## 4. Code Style & Quality

**Mandate:** All code submitted MUST pass all static analysis checks.

-   **Linting & Formatting:**
    -   Run `poetry run task format` before committing. This uses `ruff` to format the code and fix common issues.
    -   Ensure `poetry run task lint` (which runs `ruff check .`) passes without errors.
    - All the functions or methods must have a proper docstring following the google typed docstring convention.
        ```python
        def func(arg1: str, arg2: int) -> str:
            """Func does something that this docstring explains clearly.
            Args:
                arg1 (str): Description of arg1
                arg2 (int): Description of arg2
            Returns:
                str: Description of return value
            Raises:
                ValueError: Description of raised error
            """
        ```

-   **Type Checking:**
    -   All code MUST be fully type-hinted.
    -   Ensure `poetry run task typecheck` (which runs `mypy .`) passes without errors.
-   **Error Handling:**
    - The project uses an approach based on monads, any return is made by the `exc.Result` object.
        ```python
        def div(x: float | int, y: float | int) -> Result[bool]:
            try:
                return Result.Ok(x/y)
            except ZeroDivisionError as err:
                return Result.Err("a division by 0 broke the processing", src_error=err)

        res = div(2, 2)
        if res.is_ok():
            print(res.unwrap())
        else:
            print(res.unwrap_err())
        ```
    -   For any single error, the custom `Result` object from `exc.py` MUST be used to return a value or an `Error` through `Result.Err` without raising an exception.
-   **Logging:** Use the `djangoLogger` for logging application events, warnings, and errors.
- **Error as value approach**: Try avoid raise raw exceptions, use `Result.Err` from `exc.py` instead.
    ```python
    # bad! Never do this
    def do_something(parm):
        if param == 'bad condition':
            raise Exception('bad condition')
        return parm

    # very good! Always prefer this approach
    def do_something(parm: str) -> Result[str]:
        if param == 'bad condition':
            return Result.Err('bad condition', src_error=None)
        return Result.Ok(parm)
    ```

    In some cases you can use the unsure_result decorator in @utils/support.py
    ```python
    @ensure_result
    def do_something(parm):
        if param == 'bad condition':
            raise Exception('bad condition')
        return parm
    ```
- **Safe Pydantic Models:** All entities inherit from `base.entity.BaseEntity` and have to be safely created either by the `safe_create` or `safe_validate` methods.
    ```python
    # bad!
    class User(BaseEntity):
        username: str
        password: str

    user = User(username='john', password='123456')  # raises an exception!!

    # good!
    user_res = User.safe_create(username='john', password='123456')  # returns a Result object
    ```
    ```

## 5. Dependency Management

-   **Tool:** `poetry` is the sole dependency manager for this project.
-   **Adding a dependency:** Use `poetry add <package-name>`.
-   **Adding a development dependency:** Use `poetry add --group dev <package-name>`.
-   Do NOT manually edit `pyproject.toml` or `poetry.lock`.
- Always run python through poetry, never the system python.

## 6. Version Control

-   **Branching Model:** The project appears to use a GitFlow-like model.
    -   `develop`: Integration branch for new features.
    -   `main`: Stable, production-ready code.
    -   Feature branches should be created from `develop`.
-   **Commit Messages:** All commit messages MUST follow the **Conventional Commits** specification.
    -   **Format:** `<type>[optional scope]: <description>`
    -   **Examples:**
        -   `feat(clients): add password change use case`
        -   `fix(reservations): correct reservation value calculation`
        -   `refactor(payments): migrate checkout view to use service`
        -   `test(clients): add unit tests for signup entity`
        -   `docs(readme): update setup instructions`

## 7. Local Development Workflow

### Environment Setup
Before running the application, you must create a local environment file. Copy `.env-example` to a new file named `.env` and ensure all variables are correctly populated (e.g., `SECRET_KEY`, `STRIPE_API_KEY_SECRET`, `G_RECAPTCHA_KEY_SECRET`).

### Pre-Commit Checklist
To ensure code quality and the success of the CI/CD pipeline, the following commands MUST be run locally before every `git commit`:

```bash
# 1. Format code and fix linting issues
poetry run task format

# 2. Run static type checking
poetry run task typecheck

# 3. Run the entire test suite
poetry run task test
```

### Running Specific Tests
During development, you can run tests for a specific app or file to speed up the feedback loop. Use the following format:

```bash
# Run all tests in the clients app
poetry run pytest tests/unit/clients/

# Run tests for a specific file
poetry run pytest tests/unit/payments/test_usecases.py
```

## 8. Current Priorities & Action Plan

### Rewrite the task to fix issue #10

#### issue #10

---

##### Problem Statement

The tests are disorganized and somewhat untrustworthy.

##### Proposed Solution

Just rewrite it from scratch
- add coverage
-  remove unnecessary tests and redundant fixtures
- use good function names
- add proper documentation
- test only what you have made, don't test framework code (it probably was already tested)


##### Benefits

- better understanding of what is tested and what is not.
- clearer and more organized tests.
- avoids redundant or imprecise tests.
- greater reliability in test pipelines.

##### Technical Considerations

- follow the **Arrange - Act - Assert** test flow.
- write short and descriptive doc strings and names for each test function, describing what it tests.
   ```python
   def test_user_signout():
       """Should finish the user's session, then signs off the user and then redirect him to the homepage with status 302."""
   ```
- keep each test separated by its layer [domain, app, infra].
- write unique fixture functions that can be properly separated by its app domain, keeping only necessary fixtures per *conftest* file scope. Don't write fixture functions in the same file where the test functions are in.
- add **pytest-cov** and **[code-cov](https://docs.codecov.com/docs/quick-start)** for better tracking experience.

---

The old tests were moved to tests.bkp/ and the new ones is being implemented in tests/*. The tests should follow this structure:

```
tests/
├── unit/
│   ├── clients/        # App scope
│   │   ├── domain/         # domain layer tests
│   │   ├── application/         # application layer tests
│   │   └── conftest.py         # clients specific fixtures
│   ├── reservations/        # App scope
│   │    ├── domain/         # domain layer tests
│   │    ├── application/         # application layer tests
│   │    └── conftest.py         # reservations specific fixtures
│   └── conftest.py     # cross app fixtures
```


## 9. Project Overview

Current app state (should be updated after making changes)

## Dependency Injection (DI)

The application uses `dependency-injector` for dependency injection to achieve loose coupling and better testability. Each module has its own container that manages its dependencies.

### Container Setup
- **Clients Container**: `clients/container.py`
- **Reservations Container**: `reservations/container.py`
- **Payments Container**: `payments/container.py`
- **Initialization**: Containers are initialized in each app's `apps.py` file
- **Wiring**: Dependencies are wired to modules in the `ready()` method of each app

### Current Services

#### Clients Module (`clients/container.py`)
```python
# Infrastructure (Singletons)
clients_container.client_repo        # ClientRepository
clients_container.password_manager   # DjangoPasswordManager
clients_container.session_manager    # DjangoSessionManager
clients_container.captcha_service    # GoogleRecaptchaV3Verifier

# Application (Factories)
clients_container.client_service()   # ClientService instance
```

#### Reservations Module (`reservations/container.py`)
```python
# Infrastructure (Singletons)
reservations_container.reservation_repo    # ReservationRepository
reservations_container.room_repo           # RoomRepository
reservations_container.payment_repo        # PaymentRepository
reservations_container.unit_of_work        # UnitOfWork
reservations_container.task_queuer         # DjangoQTaskQueuer
reservations_container.email_sender        # DjangoEmailSender

# Use Cases (Singletons)
reservations_container.release_reservation_usecase     # ReleaseReservationUseCase
reservations_container.schedule_reservation_usecase    # ScheduleReservationUseCase
reservations_container.activate_reservation_usecase    # ActivateReservationUseCase
reservations_container.cancel_reservation_usecase      # CancelReservationUseCase

# Application (Factories)
reservations_container.reservation_service() # ReservationService instance
```

#### Payments Module (`payments/container.py`)
```python
# Infrastructure (Singletons)
payments_container.client_repo         # ClientRepository
payments_container.reservation_repo    # ReservationRepository
payments_container.room_repo           # RoomRepository
payments_container.payment_repo        # PaymentRepository
payments_container.unit_of_work        # UnitOfWork
payments_container.payment_gateway     # StripeCheckoutSession
payments_container.webhook_handler    # StripePaymentWebhookHandler
payments_container.task_queuer         # DjangoQTaskQueuer
payments_container.email_sender        # DjangoEmailSender
payments_container.pdf_generator       # ReportLabPDFReceiptGenerator

# Use Cases (Singletons)
payments_container.confirmation_usecase         # SendPaymentConfirmationUseCase
payments_container.activate_reservation_usecase # ActivateReservationUseCase
payments_container.schedule_reservation_usecase # ScheduleReservationUseCase
payments_container.release_reservation_usecase  # ReleaseReservationUseCase

# Application (Factories)
payments_container.payment_service()    # PaymentService instance
```

### Usage in Views
```python
from dependency_injector.wiring import Provide, inject
from clients.container import ClientsContainer

@inject
def setup(
    self, request, *args,
    svc: ClientService = Provide[ClientsContainer.client_service],
    **kwargs
):
    self.svc = svc
```

### Adding New Dependencies
1. **Infrastructure**: Add to container as `providers.Singleton()`
2. **Services**: Add to container as `providers.Factory()`
3. **Views**: Use `@inject` decorator with `Provide[ContainerName.service]`
4. **Wiring**: Add new modules to the `wire()` call in the app's `apps.py`

Tests override container providers using context managers:
```python
with container.service.override(mock_service):
    # Test code here
```

## Build/Lint/Test Commands

### Development Server
- `poetry run task run` - Start Django development server
- `poetry run task Q` - Start Django Q cluster for task processing

### Database
- `poetry run python manage.py migrate` - Run database migrations
- `poetry run python manage.py makemigrations` - Create new migrations
- `poetry run python manage.py check` - Check for configuration issues

### Testing
- `poetry run task test` - Run all tests with coverage
- `poetry run pytest tests/unit/path/to/test_file.py` - Run tests in specific directory
- `poetry run pytest tests/unit/path/to/test_file.py::TestClass::test_method` - Run single test method
- `poetry run pytest tests/unit/path/to/test_file.py::test_function_name` - Run single test function
- `poetry run pytest -k "test_name_pattern"` - Run tests matching pattern
- `poetry run pytest --cov=clients --cov-report=html` - Run tests with specific module coverage

### Code Quality
- `poetry run task lint` - Lint code with Ruff (preview mode)
- `poetry run task format` - Format code with Ruff and fix issues
- `poetry run task typecheck` - Type check with MyPy
- `poetry run task scan` - Scan for security vulnerabilities with Bandit
- `poetry run task pcommit` - Run all pre-commit hooks
