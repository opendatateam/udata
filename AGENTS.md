# AGENTS.md

This file provides guidance to AI agents when working with code in this repository.

## Project Overview

udata is a customizable and skinnable social platform dedicated to (open) data. It's a Flask-based Python web application that powers data.gouv.fr, the French national open data portal. The platform provides a complete open data portal solution with dataset management, harvesting, API, search, and user/organization features.

## Architecture

### Core Components

- **udata/app.py**: Application factory pattern. Creates Flask app instances with `create_app()` and `standalone()` functions. The `UDataApp` class extends Flask with custom static file handling and blueprint registration.

- **udata/core/**: Domain models and business logic organized by entity:
  - `dataset/`: Dataset and resource management (the primary content type)
  - `organization/`: Organization entities that own datasets
  - `user/`: User accounts and authentication
  - `reuse/`: Reuses (applications/visualizations using datasets)
  - `spatial/`: Geographic/territorial data and zones
  - `dataservices/`: Data service entities
  - `discussions/`: Discussion threads on datasets
  - `post/`, `topic/`, `pages/`: Editorial content

- **udata/harvest/**: Data harvesting system with pluggable backends:
  - `backends/`: Harvester implementations (DCAT, CKAN, DKAN, CSW, MAAF)
  - Harvesters are discovered via entry points (`udata.harvesters` group in pyproject.toml)
  - Enable/disable backends via `HARVESTER_BACKENDS` config setting

- **udata/api/**: REST API built with Flask-RESTX
  - Each core module typically has an `api.py` defining endpoints
  - OAuth2 authentication support in `oauth2.py`

- **udata/frontend/**: Minimal frontend utilities (markdown rendering)
  - Most frontend is in separate `udata-front` repository

- **udata/search/**: Search integration layer
  - Can integrate with external search services

- **udata/commands/**: CLI commands via Click/Flask CLI
  - `init.py`: Initialize new instance (`udata init`)
  - `serve.py`: Development server
  - `fixtures.py`: Import test/sample data
  - Each core module can define additional commands

- **udata/models/**: Legacy MongoDB/MongoEngine models (being phased out in favor of models in core modules)

- **udata/mongo/**: MongoDB connection and utilities

- **udata/migrations/**: Database migrations

- **udata/tasks.py**: Celery task registration and worker setup

### Configuration System

- Uses Flask config system with layered loading:
  1. Default settings from `udata/settings.py` (Defaults class)
  2. Environment-specific settings file (udata.cfg in working directory or path from UDATA_SETTINGS env var)
  3. Override objects passed to `create_app()`

- Key config classes:
  - `Defaults`: Production defaults
  - `Testing`: Test overrides
  - `Debug`: Development settings

### Extension Pattern

- Plugins discovered via `udata.plugins` entry point group
- Plugins must expose `init_app(app)` function
- Extensions initialized in `register_extensions()` in app.py

### Database

- MongoDB via MongoEngine ODM
- Migrations in `udata/migrations/` directory
- Run migrations with `udata db migrate`

## Development Commands

### Setup and Initialization

```bash
# Install dependencies with uv (recommended)
uv sync --extra dev

# Install with pip (alternative)
pip install -e ".[dev]"

# Initialize database, search index, create admin user, load fixtures
udata init

# Run database migrations
udata db migrate

# Load sample/test data
udata import-fixtures
```

### Running the Application

```bash
# Start development server (default port 7000)
inv serve
# or with custom host/port
inv serve --host localhost --port 7001

# Start Celery worker (required for async tasks like search indexing)
inv work
# with custom log level
inv work --loglevel debug

# Start Celery beat scheduler (for periodic tasks)
inv beat
```

### Testing

```bash
# Run all tests
inv test
# or directly with pytest
pytest udata

# Run tests with coverage
inv cover
# with HTML report
inv cover --html

# Run specific test file
pytest udata/core/dataset/tests/test_models.py

# Run specific test
pytest udata/core/dataset/tests/test_models.py::DatasetModelTest::test_create

# Run tests with verbose output
inv test --verbose

# Fast fail (stop on first failure)
inv test --fast

# Test with CI mode (no color, no sugar)
inv test --ci
```

### Code Quality

```bash
# Pre-commit hooks (initialize first)
pre-commit install

# Format and lint with ruff (done automatically by pre-commit)
ruff check --fix .
ruff format .

# Run flake8 (legacy, still used in qa task)
inv qa
```

### Internationalization

```bash
# Extract translatable strings from code
inv i18n

# Update existing translation files
inv i18n --update

# Compile translations (required before running)
inv i18nc
```

### Building and Distribution

```bash
# Clean build artifacts
inv clean

# Build wheel distribution
inv dist

# Build without cleaning
inv pydist
```

### Documentation

```bash
# Serve documentation locally with live reload
inv doc
# Opens mkdocs server at http://127.0.0.1:8000
```

### Infrastructure Services

```bash
# Start MongoDB, Redis, and Mailpit with Docker Compose
docker compose up
# Services:
# - MongoDB: localhost:27017
# - Redis: localhost:6379
# - Mailpit (email testing): http://localhost:8025 (web UI), localhost:1025 (SMTP)

# Stop services
docker compose down
```

## Testing Patterns

### Fixtures

- Use factory_boy factories in `udata/tests/factories.py` and module-specific factories
- Example: `DatasetFactory()`, `OrganizationFactory()`, `UserFactory()`
- Test fixtures auto-configured via pytest plugin in `udata/tests/plugin.py`

### Test Markers

- `@pytest.mark.frontend`: Load frontend stack
- `@pytest.mark.preview`: Mock preview backend
- `@pytest.mark.oauth`: Inject OAuth client

### Test Environment

- Test settings in `udata.settings.Testing`
- Environment variables set via pytest.ini: `AUTHLIB_INSECURE_TRANSPORT=true`
- Uses in-memory MongoDB for isolation

## Code Style Guidelines

### Python

- Follow PEP-0008, PEP-0257, PEP-0020
- Use Google Python Style Guide conventions
- Ruff handles formatting, linting, and import sorting
- Line length: 100 characters
- Imports sorted with isort-style rules (via ruff)

### Commit Messages

- Use conventional commit format
- Include issue references: `fix #123` or `(fix #123)` in commit message

### Language

- All code, comments, and documentation in English
- French translations in `udata/translations/`

## Common Patterns

### Creating New Commands

```python
# In udata/commands/mycommand.py or udata/core/mymodule/commands.py
from udata.commands import cli

@cli.command()
def mycommand():
    """Command description"""
    pass
```

Commands are auto-discovered from modules listed in `MODULES_WITH_COMMANDS` in `udata/commands/__init__.py`.

### Adding Harvester Backends

1. Create backend class inheriting from `BaseBackend` in `udata/harvest/backends/`
2. Set class attribute `name` (used for identification)
3. Register in `pyproject.toml` under `[project.entry-points."udata.harvesters"]`
4. Enable in config by adding to `HARVESTER_BACKENDS` list (supports wildcards)

Example:
```python
from udata.harvest.backends.base import BaseBackend

class MyBackend(BaseBackend):
    name = "mybackend"
    
    def harvest_single_item(self, item):
        # Implementation
        pass
```

### API Endpoints

- Use Flask-RESTX for API definitions
- Organize in module's `api.py` file
- Document with Swagger decorators
- API root is `/api/1/`

### Working with MongoEngine Models

- Models inherit from `mongoengine.Document` or module-specific base classes
- Use `db` module utilities for queries
- Migrations handle schema changes

## Important Configuration

### Development Config (udata.cfg)

Key settings for local development:
- `DEBUG = True`
- `SERVER_NAME = 'localhost:7000'`
- `URLS_ALLOW_LOCAL = True`
- `URLS_ALLOW_PRIVATE = True`
- `CACHE_TYPE = 'null'`
- `FS_ROOT`: Path to file storage directory
- `HARVESTER_BACKENDS`: List of enabled harvester backends

### Feature Flags

- `PUBLISH_ON_RESOURCE_EVENTS`: Enable/disable resource event publishing
- `POST_DISCUSSIONS_ENABLED`: Enable discussion posts
- `READ_ONLY_MODE`: Disable write operations (for spam mitigation)
- `ACTIVATE_TERRITORIES`: Enable territorial features

## Related Projects

- **udata-front**: Frontend application (separate repository)
- **datagouv-components**: Component library (imported as `@datagouv/components-next` outside datagouv-components folder)

## Entry Points

The project uses setuptools entry points for extensibility:
- `udata.harvesters`: Harvester backends
- `udata.plugins`: Platform plugins
- `udata.i18n`: Translation domains
- `pytest11`: udata pytest plugin

## Key Files

- `pyproject.toml`: Project metadata, dependencies, and build configuration
- `udata.cfg`: Local configuration (not in git, created per-instance)
- `manage.py`: Development launcher (runs with debug settings)
- `babel.cfg`: i18n extraction configuration
- `.pre-commit-config.yaml`: Pre-commit hook configuration
- `docker-compose.yml`: Local service dependencies
