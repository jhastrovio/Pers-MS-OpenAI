# Pers MS OpenAI

## Project Overview

This repository contains a proof-of-concept for integrating Microsoft Graph data with OpenAI services.  The system ingests emails, attachments, and documents from Microsoft Graph and OneDrive, cleans them, and stores the results in OneDrive and an OpenAI vector store for retrieval via a FastAPI backend.

## Setup

1. **Python**: The project requires Python 3.11 or newer as specified in `pyproject.toml`.
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   (Optional) install test dependencies with:
   ```bash
   pip install -r requirements-test.txt
   ```
3. **Environment configuration**: create a `.env` file in the repository root and provide the required variables.  The configuration module reads variables such as `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID`, `USER_EMAIL`, `OPENAI_API_KEY`, `OPENAI_VECTOR_STORE_ID`, and `OPENAI_VECTOR_STORE_NAME`.

## Running Checks

Run linting and the test suite before opening a pull request:
```bash
make lint test
```
This command formats the code and executes the test suite as referenced in `agents.md`.

## Further Reading

See [docs/ROADMAP.md](docs/ROADMAP.md) for implementation plans and [docs/design_decisions.md](docs/design_decisions.md) for architectural decisions.
