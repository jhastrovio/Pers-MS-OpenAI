# Personal MS Assistant ChatGPT Actions

A FastAPI-based API for integrating ChatGPT Actions with your personal Microsoft data and assistant capabilities.

## Features
- Secure, modular FastAPI server
- Real data access endpoints
- API key authentication (default)
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

### Example `.env` variables
```
P_Deploy_API_Key=your_api_key_here
CLIENT_ID=your_azure_ad_client_id
CLIENT_SECRET=your_azure_ad_client_secret
TENANT_ID=your_azure_ad_tenant_id
USER_EMAIL=your_user_email
AZURE_OPENAI_API_KEY=your_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_COMPLETION_DEPLOYMENT_ID=your-chat-deployment-name
AZURE_EMBEDDING_DEPLOYMENT_ID=your-embedding-deployment-name
AZURE_OPENAI_API_VERSION=2023-05-15
```

## Running the Server
```bash
python app.py
```
The API will be available at `http://localhost:8000` (see `/docs` for OpenAPI UI).

## Running Tests
```bash
pytest
```

## Azure Deployment
- Set all required environment variables in Azure App Service Application settings.
- Restart the app after making changes.

## More Information
See [ROADMAP.md](./ROADMAP.md) for project goals, architecture, and detailed checklist.
