# Test Suite Documentation

## Overview
This directory contains the test suite for the Pers-MS-OpenAI project. The tests are organized to mirror the structure of the main codebase, with each module having its corresponding test module.

## Directory Structure
```
tests/
├── utils/                 # Tests for utility modules
│   ├── test_config.py    # Configuration utility tests
│   ├── test_logging.py   # Logging utility tests
│   └── test_helpers.py   # Helper functions tests
└── .archive/             # Archived legacy test files
```

## Test Categories

### Utility Tests (`utils/`)
- **Configuration Tests** (`test_config.py`): Tests for environment variable management and configuration validation
- **Logging Tests** (`test_logging.py`): Tests for logger initialization and singleton pattern
- **Helper Tests** (`test_helpers.py`): Tests for common utility functions like timestamp formatting and file operations

## Running Tests
To run the test suite:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/utils/test_config.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=core
```

## Test Conventions
1. Each test file is named `test_*.py`
2. Test functions are named `test_*`
3. Each test function has a descriptive docstring
4. Tests are independent and can run in any order
5. Tests use pytest fixtures for setup and teardown

## Legacy Code
Legacy test files have been moved to the `.archive` directory. These files are kept for reference but are not part of the active test suite.

## Adding New Tests
When adding new tests:
1. Create test files in the appropriate subdirectory
2. Follow the existing naming conventions
3. Include comprehensive docstrings
4. Add test cases for both success and failure scenarios
5. Use appropriate pytest fixtures for setup 