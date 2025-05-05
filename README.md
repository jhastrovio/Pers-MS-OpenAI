# Personal MS Assistant ChatGPT Actions

A FastAPI-based API for integrating ChatGPT Actions with your personal Microsoft data and assistant capabilities.

## Features
- Secure, modular FastAPI server
- Real data access endpoints
- Simple authentication (API key or JWT)
- OpenAPI schema for ChatGPT integration

## Setup
1. **Clone the repository**
2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure environment:**
   - Copy `.env.example` to `.env` (if available) or create a `.env` file
   - Fill in required secrets and config values

## Running the Server
```bash
python app.py
```
The API will be available at `http://localhost:8000` (see `/docs` for OpenAPI UI).

## Running Tests
```bash
pytest
```

## More Information
See [ROADMAP.md](./ROADMAP.md) for project goals, architecture, and detailed checklist.
